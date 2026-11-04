import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score, brier_score_loss
from .data import read, DB

FEATURES=['available','daily_demand','lead_time_days','inbound_units','days_cover']

def features(df):
    x=df.copy()
    x['days_cover']=x.available/x.daily_demand.clip(lower=.1)
    return x[FEATURES]


def train(path=DB):
    hist=read('SELECT * FROM training_snapshots',path)
    dates=sorted(hist.snapshot_date.unique())
    train=hist[hist.snapshot_date<dates[-4]]
    test=hist[hist.snapshot_date>=dates[-3]]  # one week purged between train and test
    model=RandomForestClassifier(n_estimators=180,max_depth=6,min_samples_leaf=8,random_state=42,n_jobs=1)
    model.fit(features(train),train.stockout_next_7d)
    p=model.predict_proba(features(test))[:,1]
    y=test.stockout_next_7d
    baseline=(features(test).days_cover<7).astype(int)
    metrics={'train_rows':len(train),'test_rows':len(test),'test_start':dates[-3],
        'roc_auc':round(roc_auc_score(y,p),4),'average_precision':round(average_precision_score(y,p),4),
        'precision_at_50pct':round(precision_score(y,p>=.5,zero_division=0),4),'recall_at_50pct':round(recall_score(y,p>=.5,zero_division=0),4),
        'brier_score':round(brier_score_loss(y,p),4),'baseline_brier':round(brier_score_loss(y,baseline),4),
        'prevalence':round(y.mean(),4),'train_end':str(train.snapshot_date.max())}
    current=read('SELECT * FROM sku_summary',path)
    current['inbound_units']=0  # no inbound feed in demo database
    current['risk_score']=model.predict_proba(features(current))[:,1]
    current['risk_band']=pd.cut(current.risk_score,[-1,.3,.65,1],labels=['Low','Watch','High'])
    current['reason']=current.apply(lambda r:f'{r.available} available • {r.daily_demand:.1f} units/day • {r.days_cover:.1f} days cover',axis=1)
    return model,current.sort_values('risk_score',ascending=False),metrics
