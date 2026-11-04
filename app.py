import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pickpilot.data import DB, generate, read
from pickpilot.risk import train
from pickpilot.query import EXAMPLES, generate_sql, safe_query
from pickpilot.operations import slotting, route

st.set_page_config(page_title='PickPilot AI | Operations desk',page_icon='◈',layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem;max-width:1500px}h1{letter-spacing:-1.8px!important;font-size:2.7rem!important}h2{letter-spacing:-.6px} [data-testid="stMetric"]{background:white;border:1px solid #DFE6EC;border-radius:12px;padding:18px} [data-testid="stSidebar"]{background:#142C39} [data-testid="stSidebar"] *{color:#EDF4F7} .eyebrow{font-size:12px;letter-spacing:2px;color:#008377;font-weight:700}.hero{background:#E6F3EF;padding:20px 25px;border-radius:12px;border-left:4px solid #008377;margin:16px 0 26px}.hero b{font-size:20px} .stTabs [data-baseweb="tab"]{font-size:16px;padding:12px 20px}footer{visibility:hidden}
</style>''',unsafe_allow_html=True)
if not DB.exists(): generate()
@st.cache_resource
def load(): return train()
model,scores,metrics=load()
with st.sidebar:
    st.markdown('## ◈ PickPilot AI')
    st.caption('WAREHOUSE OPERATIONS COPILOT')
    st.markdown('---')
    st.markdown('**CHI-01 · Demo warehouse**')
    st.caption('Snapshot · November 4, 2026')
    st.markdown('---')
    view=st.radio('Workspace',['Operations overview','Ask inventory','Stockout risk','Slotting & routes','Validation'],label_visibility='collapsed')
    st.markdown('---')
    st.caption('SYNTHETIC DATA ONLY')
    st.caption('150 SKUs · 100 locations\n\n10,000 operational rows\n\nSQLite + scikit-learn')
    st.caption('Oracle WMS-style entities; no Oracle connection or compatibility claim.')
st.markdown('<div class="eyebrow">PICKPILOT / OPERATIONS DESK</div>',unsafe_allow_html=True)
st.title(view)
st.caption('Turn warehouse signals into the next best action.  •  Prototype / CHI-01')

if view=='Operations overview':
    high=int((scores.risk_score>=.65).sum()); slow=int((scores.days_cover>30).sum())
    st.markdown(f'<div class="hero"><b>{high} SKUs need a replenishment review</b><br>Review seven-day stockout signals, then investigate pick exceptions and slotting opportunities.</div>',unsafe_allow_html=True)
    cols=st.columns(4)
    for col,label,value,helptext in zip(cols,['Available units','High-risk SKUs','Pick exceptions','Slow-moving SKUs'],[f'{scores.available.sum():,}',high,int(scores.exceptions.sum()),slow],['On hand less allocated','Model score ≥ 65%','Short picks + blocked locations','More than 30 days of cover']):
        col.metric(label,value); col.caption(helptext)
    a,b=st.columns([1.4,1])
    with a:
        st.subheader('Replenishment watchlist')
        fig=px.bar(scores.head(10).sort_values('risk_score'),x='risk_score',y='sku',orientation='h',color_discrete_sequence=['#008377'],hover_data=['available','days_cover'])
        fig.update_layout(height=350,xaxis_tickformat='.0%',xaxis_title='Synthetic 7-day risk score',yaxis_title='',margin=dict(l=0,r=10,t=10,b=10),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,use_container_width=True)
    with b:
        st.subheader('Supervisor action queue')
        st.info('01 · Replenishment\n\nReview high-risk SKUs and supplier lead times before releasing the next wave.')
        st.warning('02 · Pick exceptions\n\nCheck short picks against allocated stock and inspect blocked bins.')
        st.success(f'03 · Slotting\n\n{len(slotting())} feasible moves into vacant forward bins are ready for review.')
    st.subheader('Priority SKUs')
    st.dataframe(scores[['sku','description','risk_score','available','daily_demand','days_cover','exceptions']].head(8),hide_index=True,use_container_width=True,column_config={'risk_score':st.column_config.ProgressColumn('Risk score',min_value=0,max_value=1,format='percent')})

elif view=='Ask inventory':
    st.subheader('Ask a warehouse question')
    live=st.toggle('Live LLM',value=False)
    st.caption('Live mode sends your question and database schema to OpenAI. Demo mode uses four fixed SQL templates; it is not an LLM.')
    example=st.selectbox('Try a question',list(EXAMPLES))
    question=st.text_input('Your question',value=example,max_chars=1000)
    if st.button('Ask PickPilot',type='primary'):
        try:
            with st.spinner('Preparing and checking SQL…'):
                sql=generate_sql(question,live)
                frame,truncated=safe_query(sql)
            st.success(f'{len(frame)} rows returned'+(' · results capped at 200 rows' if truncated else ''))
            st.code(sql,language='sql')
            st.dataframe(frame,hide_index=True,use_container_width=True)
            if not frame.empty:
                st.write('**Answer from the executed query:**')
                st.write(f'{len(frame)} matching result rows. First result: '+ '; '.join(f'{c}: {v}' for c,v in frame.iloc[0].items()))
            else: st.info('No matching records for this question.')
            st.download_button('Download answer CSV',frame.to_csv(index=False),'inventory-answer.csv','text/csv')
        except Exception as exc:
            st.error(f'Query could not be completed: {exc}')

elif view=='Stockout risk':
    st.subheader('Seven-day replenishment signals')
    st.caption('Random forest scores trained on synthetic weekly scenarios. No inbound feed is available for the current snapshot; inbound is assumed zero. Scores are uncalibrated model estimates.')
    threshold=st.slider('Minimum risk score',0,100,65)/100
    categories=st.multiselect('Category',sorted(scores.category.unique()))
    selected=scores[scores.risk_score>=threshold]
    if categories: selected=selected[selected.category.isin(categories)]
    st.dataframe(selected[['sku','description','category','risk_score','risk_band','reason','lead_time_days']],hide_index=True,use_container_width=True,column_config={'risk_score':st.column_config.ProgressColumn('Risk score',min_value=0,max_value=1,format='percent')})
    st.download_button('Export replenishment review',selected.to_csv(index=False),'risk-review.csv','text/csv')
    st.subheader('Model drivers across the training scenarios')
    importance=pd.DataFrame({'Feature':model.feature_names_in_,'Importance':model.feature_importances_}).sort_values('Importance')
    st.plotly_chart(px.bar(importance,x='Importance',y='Feature',orientation='h',color_discrete_sequence=['#008377']),use_container_width=True)
    st.caption('Global feature importance describes model behavior; it does not establish causes of stockouts.')

elif view=='Slotting & routes':
    st.subheader('Move fast movers closer to dispatch')
    moves=slotting()
    st.caption('Heuristic: highest-demand reserve SKUs first, vacant forward bins only, capacity checked. Distances are modeled one-way meters per pick; no realized savings claimed.')
    st.dataframe(moves,hide_index=True,use_container_width=True)
    st.download_button('Export proposed moves',moves.to_csv(index=False),'slotting-review.csv','text/csv')
    st.subheader('Explore a pick route')
    order_ids=read('SELECT order_id FROM order_lines GROUP BY order_id HAVING COUNT(*)>=5 ORDER BY order_id').order_id.tolist()
    order=st.selectbox('Order',order_ids)
    bins,before,after=route(order)
    c1,c2,c3=st.columns(3); c1.metric('Bin-code sequence',f'{before:.0f} m'); c2.metric('Proposed route',f'{after:.0f} m'); c3.metric('Modeled reduction',f'{(before-after)/before:.0%}' if before else '0%')
    st.caption('Visits both storage bins per SKU for illustration, using Manhattan distance and nearest neighbor with return to dispatch. This is not an allocation plan; stock feasibility, congestion, and one-way aisles are not modeled.')
    fig=go.Figure()
    x=[0]+(bins.aisle*9).tolist()+[0]; y=[0]+(bins.bay*2.4).tolist()+[0]
    fig.add_trace(go.Scatter(x=x,y=y,mode='lines+markers+text',text=['Dispatch']+bins.stop.astype(str).tolist()+[''],textposition='top center',line=dict(color='#008377',width=3),marker=dict(size=10)))
    fig.update_layout(height=360,xaxis_title='Aisle distance (m)',yaxis_title='Bay distance (m)',showlegend=False)
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(bins,hide_index=True,use_container_width=True)
else:
    st.subheader('Evidence, assumptions & boundaries')
    st.info('Prototype validation on synthetic data. No warehouse user study, Oracle integration, or production outcome has been validated.')
    c=st.columns(3); c[0].metric('Held-out ROC AUC',f'{metrics["roc_auc"]:.3f}'); c[1].metric('Average precision',f'{metrics["average_precision"]:.3f}'); c[2].metric('Brier score ↓',f'{metrics["brier_score"]:.3f}')
    st.json(metrics)
    st.write('Temporal holdout: 12 weekly cutoffs for training, one cutoff purged, last three for testing. Label: future seven-day demand exceeds available stock plus inbound arriving within seven days. Features exclude future demand and labels. The same SKUs recur across time, so this does not test unseen SKU generalization.')
    st.write('Demand history is generated independently from operational events. Current daily demand is requested order units over 28 days, not completed picks. Synthetic scenario metrics do not predict real warehouse performance. Before use: reconcile inventory, add inbound timing, test calibration, review routing constraints, and validate with supervisors.')
    st.download_button('Download model validation JSON',json.dumps(metrics,indent=2),'model-validation.json','application/json')
