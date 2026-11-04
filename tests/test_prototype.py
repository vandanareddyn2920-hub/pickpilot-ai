import sqlite3
import pytest
from pickpilot.data import generate, read, connect
from pickpilot.query import safe_query, EXAMPLES, generate_sql
from pickpilot.risk import train
from pickpilot.operations import slotting, route

@pytest.fixture(scope='module')
def db(tmp_path_factory): return generate(tmp_path_factory.mktemp('warehouse')/'test.db')

def test_data_integrity(db):
    tables=['items','locations','inventory','orders','order_lines','picks']
    assert sum(read(f'SELECT COUNT(*) n FROM {t}',db).n[0] for t in tables)==10000
    with connect(db) as con: assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert read('SELECT COUNT(*) n FROM inventory WHERE allocated>on_hand OR allocated<0',db).n[0]==0
    assert read('SELECT COUNT(*) n FROM sku_summary',db).n[0]==150

@pytest.mark.parametrize('question',EXAMPLES)
def test_demo_queries(db,question):
    result,capped=safe_query(generate_sql(question),db)
    assert not capped
    assert not result.empty

@pytest.mark.parametrize('sql',["DELETE FROM inventory","SELECT * FROM training_snapshots","SELECT * FROM sqlite_master","SELECT load_extension('x')","SELECT * FROM items; DELETE FROM items;","WITH x AS (SELECT 1) DELETE FROM items"])
def test_sql_boundary(db,sql):
    with pytest.raises((ValueError,sqlite3.DatabaseError)): safe_query(sql,db)

def test_bounds_and_timeout(db):
    frame,truncated=safe_query('SELECT * FROM picks',db,max_rows=5)
    assert len(frame)==5 and truncated
    with pytest.raises(sqlite3.DatabaseError):
        safe_query('WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT SUM(n) FROM x',db,timeout=.01)

def test_ml(db):
    _,scores,m=train(db)
    assert len(scores)==150 and scores.risk_score.between(0,1).all()
    assert m['train_end']<m['test_start'] and m['test_rows']==450
    assert m['roc_auc']>.7

def test_proposals(db):
    moves=slotting(db)
    assert not moves.empty
    assert moves.to_bin.is_unique and (moves.estimated_m_per_pick>0).all()
    occupied=read('SELECT DISTINCT location_id FROM inventory',db).location_id
    assert not moves.to_bin.isin(occupied).any()
    order=read('SELECT order_id FROM order_lines GROUP BY order_id HAVING COUNT(*)>=5 LIMIT 1',db).order_id[0]
    bins,before,after=route(order,db)
    assert len(bins)>0 and after<=before

def test_live_api_wiring(db,monkeypatch):
    import types
    import openai
    calls={}
    class FakeClient:
        def __init__(self,**kwargs): self.responses=self
        def create(self,**kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(output_text='SELECT COUNT(*) AS skus FROM items')
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    monkeypatch.setattr(openai,'OpenAI',FakeClient)
    sql=generate_sql('How many SKUs?',live=True,path=db)
    frame,_=safe_query(sql,db)
    assert frame.skus[0]==150
    assert calls['store'] is False and calls['input']=='How many SKUs?'
    assert 'CREATE TABLE items' in calls['instructions']


def test_streamlit_views(db):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    for view in ['Ask inventory','Stockout risk','Slotting & routes','Validation']:
        app.sidebar.radio[0].set_value(view).run(timeout=30)
        assert not app.exception
        if view=='Ask inventory':
            app.button[0].click().run(timeout=30)
            assert not app.exception and app.success
