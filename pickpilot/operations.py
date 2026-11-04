import pandas as pd
from .data import read, DB


def slotting(path=DB):
    # Move into vacant forward bins only; no collisions, capacity checked.
    occupied=read('SELECT DISTINCT location_id FROM inventory',path).location_id.tolist()
    vacant=read("SELECT * FROM locations WHERE zone='Forward' ORDER BY distance_m",path)
    vacant=vacant[~vacant.location_id.isin(occupied)].to_dict('records')
    candidates=read('''SELECT i.sku,i.location_id,i.on_hand,l.distance_m,s.daily_demand,s.description
    FROM inventory i JOIN locations l USING(location_id) JOIN sku_summary s USING(sku)
    WHERE l.zone='Reserve' AND s.daily_demand>4 AND i.on_hand>0
    ORDER BY s.daily_demand DESC''',path)
    result=[]
    for r in candidates.itertuples():
        target=next((v for v in vacant if v['capacity_units']>=r.on_hand and v['distance_m']<r.distance_m),None)
        if target:
            vacant.remove(target)
            result.append(dict(sku=r.sku,description=r.description,from_bin=r.location_id,to_bin=target['location_id'],units=r.on_hand,daily_demand=r.daily_demand,estimated_m_per_pick=round(r.distance_m-target['distance_m'],1)))
    return pd.DataFrame(result,columns=['sku','description','from_bin','to_bin','units','daily_demand','estimated_m_per_pick'])


def route(order_id,path=DB):
    # Rectilinear one-way aisle centers; start/end at (0,0).
    bins=read('''SELECT DISTINCT l.location_id,l.aisle,l.bay FROM order_lines ol
    JOIN inventory i USING(sku) JOIN locations l USING(location_id) WHERE ol.order_id=?'''.replace('?',"'"+order_id.replace("'","''")+"'"),path)
    if bins.empty: return bins,0,0
    points={r.location_id:(r.aisle*9,r.bay*2.4) for r in bins.itertuples()}
    def distance(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
    def length(sequence):
        pts=[(0,0)]+[points[k] for k in sequence]+[(0,0)]
        return round(sum(distance(a,b) for a,b in zip(pts,pts[1:])),1)
    baseline=sorted(points)
    remaining=set(points); sequence=[]; pos=(0,0)
    while remaining:
        k=min(remaining,key=lambda k:(distance(pos,points[k]),k)); sequence.append(k); remaining.remove(k); pos=points[k]
    # Return best of heuristic and existing sequence.
    if length(sequence)>length(baseline): sequence=baseline
    ordered=bins.set_index('location_id').loc[sequence].reset_index()
    ordered['stop']=range(1,len(ordered)+1)
    return ordered,length(baseline),length(sequence)
