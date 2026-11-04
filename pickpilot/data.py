"""Deterministic, fictional WMS-style data; no Oracle schema compatibility claimed."""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'warehouse.db'
AS_OF = pd.Timestamp('2026-11-04')

DDL = '''
CREATE TABLE items (sku TEXT PRIMARY KEY, description TEXT, category TEXT, unit_cost REAL, lead_time_days INTEGER);
CREATE TABLE locations (location_id TEXT PRIMARY KEY, zone TEXT, aisle INTEGER, bay INTEGER, distance_m REAL, capacity_units INTEGER);
CREATE TABLE inventory (sku TEXT REFERENCES items(sku), location_id TEXT REFERENCES locations(location_id), on_hand INTEGER CHECK(on_hand>=0), allocated INTEGER CHECK(allocated>=0 AND allocated<=on_hand), PRIMARY KEY(sku,location_id));
CREATE TABLE orders (order_id TEXT PRIMARY KEY, order_date TEXT, status TEXT);
CREATE TABLE order_lines (line_id INTEGER PRIMARY KEY, order_id TEXT REFERENCES orders(order_id), sku TEXT REFERENCES items(sku), requested_qty INTEGER);
CREATE TABLE picks (pick_id INTEGER PRIMARY KEY, line_id INTEGER REFERENCES order_lines(line_id), location_id TEXT REFERENCES locations(location_id), picked_qty INTEGER, status TEXT, travel_seconds REAL, pick_date TEXT);
'''

def generate(path=DB, seed=42):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    skus = [f'SKU-{i:04}' for i in range(1,151)]
    cats = ['Apparel','Home','Electronics','Health','Outdoors']
    names = ['Trail bottle','Cotton tee','USB adapter','Care kit','Storage bin','Packing tape']
    items = pd.DataFrame([dict(sku=s, description=f'{names[i%6]} {i+1}', category=cats[i%5], unit_cost=round(rng.uniform(3,95),2), lead_time_days=int(rng.integers(3,15))) for i,s in enumerate(skus)])
    locations = pd.DataFrame([dict(location_id=f'A{i//10+1:02}-B{i%10+1:02}', zone='Forward' if i<30 else 'Reserve', aisle=i//10+1, bay=i%10+1, distance_m=round(8+(i//10)*9+(i%10)*2.4,1), capacity_units=1000) for i in range(100)])
    rates = rng.lognormal(1.2,.8,150)
    inv=[]
    for i,s in enumerate(skus):
        for k in range(2):
            qty=int(min(900,rates[i]*rng.uniform(.4,16)))
            inv.append((s,locations.location_id[(list(range(20))+list(range(30,100)))[(i*7+k*37)%90]],qty,int(qty*rng.uniform(0,.35))))
    inventory=pd.DataFrame(inv,columns=['sku','location_id','on_hand','allocated'])
    orders=pd.DataFrame([dict(order_id=f'ORD-{i:05}',order_date=(AS_OF-pd.Timedelta(days=int(rng.integers(0,28)))).date().isoformat(),status='Released' if i%7==0 else 'Complete') for i in range(1200)])
    weights=rates/rates.sum()
    lines=pd.DataFrame({'line_id':np.arange(1,4251),'order_id':rng.choice(orders.order_id,4250),'sku':rng.choice(skus,4250,p=weights),'requested_qty':rng.integers(1,9,4250)})
    joined=lines.iloc[:4000].merge(orders,on='order_id').merge(inventory.drop_duplicates('sku')[['sku','location_id']],on='sku').merge(locations,on='location_id')
    statuses=rng.choice(['Complete','Short pick','Location blocked'],4000,p=[.90,.075,.025])
    picks=pd.DataFrame({'pick_id':np.arange(1,4001),'line_id':joined.line_id,'location_id':joined.location_id,'picked_qty':np.where(statuses=='Complete',joined.requested_qty,np.maximum(joined.requested_qty-2,0)),'status':statuses,'travel_seconds':np.round(joined.distance_m*1.6+rng.uniform(8,32,4000),1),'pick_date':joined.order_date})
    # Extra training scenarios are independent weekly historical snapshots.
    # Features are observed at cutoff; labels use a new seven-day demand draw.
    hist=[]
    for week in range(16):
        for i,s in enumerate(skus):
            demand=max(.1,rates[i]*rng.lognormal(0,.25))
            observed=rng.poisson(demand*14)/14
            available=int(demand*rng.uniform(.1,18))
            inbound=int(demand*rng.uniform(0,7)) if rng.random()<.45 else 0
            lead=int(items.lead_time_days.iloc[i])
            future=rng.negative_binomial(10,10/(10+demand*7))
            hist.append((s,(AS_OF-pd.Timedelta(weeks=16-week)).date().isoformat(),available,observed,lead,inbound,int(future>available+(inbound if lead<=7 else 0))))
    snapshots=pd.DataFrame(hist,columns=['sku','snapshot_date','available','daily_demand','lead_time_days','inbound_units','stockout_next_7d'])
    if path.exists(): path.unlink()
    with sqlite3.connect(path) as con:
        con.executescript(DDL)
        for name,frame in [('items',items),('locations',locations),('inventory',inventory),('orders',orders),('order_lines',lines),('picks',picks)]:
            frame.to_sql(name,con,if_exists='append',index=False)
        snapshots.to_sql('training_snapshots',con,index=False)
        con.executescript('''
        CREATE VIEW sku_summary AS
        WITH demand AS (
          SELECT ol.sku, SUM(ol.requested_qty)/28.0 AS daily_demand FROM order_lines ol GROUP BY ol.sku
        ), stock AS (
          SELECT sku, SUM(on_hand) AS on_hand, SUM(allocated) AS allocated, SUM(on_hand-allocated) AS available FROM inventory GROUP BY sku
        ), exceptions AS (
          SELECT ol.sku, SUM(CASE WHEN p.status!='Complete' THEN 1 ELSE 0 END) AS exceptions, COUNT(*) AS pick_count
          FROM picks p JOIN order_lines ol ON p.line_id=ol.line_id GROUP BY ol.sku
        )
        SELECT i.*,s.on_hand,s.allocated,s.available,ROUND(COALESCE(d.daily_demand,0),3) AS daily_demand,
        ROUND(s.available/NULLIF(d.daily_demand,0),2) AS days_cover,COALESCE(e.exceptions,0) AS exceptions,COALESCE(e.pick_count,0) AS pick_count
        FROM items i JOIN stock s USING(sku) LEFT JOIN demand d USING(sku) LEFT JOIN exceptions e USING(sku);
        ''')
    return path


def connect(path=DB):
    return sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro',uri=True)


def read(sql,path=DB):
    with connect(path) as con:
        return pd.read_sql_query(sql,con)

if __name__=='__main__':
    print(generate())
