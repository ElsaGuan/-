'''
市值轮动策略：每一个月根据新的市值排名，将持仓调整为新的组合股票
'''

import pandas as pd
from jqdata import *


def initialize(context):
    # 循环周围为每天
    run_daily(daily,time='every_bar')
    # 初始化全局参数
    set_params()
    # 基准为上证指数
    set_benchmark('000001.XSHG')       

    set_option('use_real_price', True) 
    log.set_level('order', 'error') 
    
def set_params():
    
    # 记录策略进行到第几天，初始为0
    g.days = 0 
    # 调仓周期：一个月
    g.period = 21  
    # 0.1分位
    g.precent = 0.10       
    # 股票池
    g.index='000001.XSHG' 
    g.quantile = (0,10)

 
# 设置可行股票池
# 过滤掉当日停牌的股票,且筛选出前days天未停牌股票
# 输入：stock_list为list类型,天数days为int类型
# 输出：可交易的股票list
def set_feasible_stocks(stock_list,days,context):
    # 得到是否停牌信息的dataframe，停牌的1，未停牌得0
    suspened_info_df = get_price(list(stock_list), start_date=context.current_dt, end_date=context.current_dt, frequency='daily', fields='paused')['paused'].T
    # 过滤停牌股票 返回dataframe
    unsuspened_index = suspened_info_df.iloc[:,0]<1
    # 得到当日未停牌股票的代码list:
    unsuspened_stocks = suspened_info_df[unsuspened_index].index
    # 进一步，筛选出前days天未曾停牌的股票list:
    feasible_stocks = []
    current_data = get_current_data()
    for stock in unsuspened_stocks:
        if sum(attribute_history(stock, days, unit = '1d',fields = ('paused'), skip_paused = False))[0] == 0:
            feasible_stocks.append(stock)
            
    return feasible_stocks
    
    
# 获取分位内的股票
# 取可交易股票的流动市值，以流动市值的大小排序，取分位内的股票
# 输入：stock_list为list类型
# 输出：股票list   
def get_stocks(stock_list, context):
    # 获得流通市值 circulating_market_cap 流通市值(亿)
    df_CMC = get_fundamentals(query(valuation.code, valuation.circulating_market_cap
                     ).filter(valuation.code.in_(stock_list)))
    # 删除nan
    df_CMC = df_CMC.dropna()
    # 生成排名序数
    df_CMC['CMC_sorted_rank'] = df_CMC['circulating_market_cap'].rank(ascending = False, method = 'dense')
    # 使用股票代码作为index
    df_CMC.set_index('code',drop = True, inplace = True)
    df_CMC.columns = ['CMC', 'CMC_sorted_rank']
    # 按市值打分排序，市值大的序号小
    df_CMC.sort('CMC_sorted_rank',ascending = False,inplace = True)
    print(df_CMC)
    stocks = list(df_CMC.index)
    return stocks
    

# 将回测的quantile参数作为输入参数
# 以获得不同quantile下的回测结果
def rebalance(context, holding_list, start_q, end_q, total_number):
    # if end_q == 100:
    #     end_q = 100
    
    # 空仓只有买入操作
    stocks = holding_list[start_q * total_number / 100 : end_q * total_number / 100]
    print(stocks)
    # 每只股票购买金额
    every_stock = context.portfolio.portfolio_value/len(stocks)
    
    if len(list(context.portfolio.positions.keys()))==0:
        # 原设定重scort始于回报率相关打分计算，回报率是升序排列
        for stock_to_buy in stocks: 
            order_target_value(stock_to_buy, every_stock)
    else :
        # 不是空仓先卖出持有但是不在购买名单中的股票
        for stock_to_sell in list(context.portfolio.positions.keys()):
            if stock_to_sell not in stocks:
                order_target_value(stock_to_sell, 0)
        # 买入在购买名单中的股票
        for stock_to_buy in stocks: 
            order_target_value(stock_to_buy, every_stock)
        # for stock_to_buy in stocks: 
        #     order_target_value(stock_to_buy, every_stock)


def daily(context):
    # 判断策略进行天数是否能被轮动频率整除
    if g.days % g.period == 0:
        
        # 股票池
        scu = get_index_stocks(g.index)
        # 可交易股票池
        feasible_stocks = set_feasible_stocks(scu,g.period,context)
        # 根据市值选取的应买入的股票
        holding_list = get_stocks(feasible_stocks, context)
        
        total_num = len(holding_list)
        (start_q, end_q) = g.quantile
        
        # 调仓
        rebalance(context,holding_list,start_q,end_q,total_num)
    else:
        pass # 什么也不做

    g.days = g.days + 1 # 策略经过天数增加1