from handle.metric_collect import MetricExplorer

# endpoint: 字符串类型，表示API端点的名称，例如 "GET:/api/v1/orderservice/order/security/{checkDate}/{accountId}"。

# minute: 字符串类型，遵循 "YYYY-MM-DD HH:MM" 格式，表示统计数据对应的时间。例如 "2024-01-09 09:00"。

# calls: 整数，表示在给定时间点对相应端点的调用次数。

# success_rate: 浮点类型，表示成功请求的百分比。计算公式为 (1 - 错误请求数 / 总调用数) * 100。

# error_rate: 浮点类型，表示错误请求的百分比。计算公式为 (错误请求数 / 总调用数) * 100。

# average_duration: 浮点类型，表示平均响应时间（以毫秒为单位）。计算公式为 总响应时间 / 总调用数。

explorer = MetricExplorer()

def query_endpoint_stats(endpoint: str, minute: str) -> dict:
    """
    This function retrieves the statistics for a specific API endpoint at a specific time.
    
    Parameters:
    - endpoint (str): The unique identifier of the API endpoint to be queried. 
    - minute (str): The specific time at which statistics are to be queried, formatted as "YYYY-MM-DD HH:MM". 
    
    Returns:
    - dict: A dictionary containing the statistical data of the specified endpoint at the specified time. 
      If no data is available, returns an empty dict {} - this means the endpoint had no activity at that time.
      The dictionary includes the following keys:
        - 'calls' (int): The total number of requests made to the endpoint.
        - 'success_rate' (float): The percentage of requests that completed successfully. 
          This is calculated as (1 - Number of Bad Requests / Total Number of Calls) * 100.
        - 'error_rate' (float): The percentage of requests that resulted in an error. 
          This is calculated as (Number of Error Requests / Total Number of Calls) * 100.
        - 'average_duration' (float): The average response time of the requests in milliseconds. 
          This is calculated as (Total Response Time / Total Number of Calls).
    """
    endpoint_data = explorer.query_endpoint_stats(endpoint, minute)
    return endpoint_data

def query_endpoint_metrics_in_range(endpoint: str, minute: str) -> dict:
    """
    This function retrieves the statistics for a specific API endpoint over a specified time range. 
    The time range is centered around the provided time, spanning from 15 minutes before to 5 minutes after.
    
    Parameters:
    - endpoint (str): The unique identifier of the API endpoint to be queried. 
    - minute (str): The central time point around which the statistics are to be queried, formatted as "YYYY-MM-DD HH:MM:SS". 
    
    Returns:
    - dict: A dictionary containing aggregated statistical data for the specified endpoint over the specified time range. 
      If no data is available for the endpoint, the returned dict will contain all zero values for each time minute.
      The dictionary includes the following keys (for each minute in the range):
        - 'calls' (int): The total number of requests made to the endpoint within the time range.
        - 'success_rate' (float): The average percentage of successful requests. 
          Calculated as (1 - Number of Bad Requests / Total Number of Calls) * 100.
        - 'error_rate' (float): The average percentage of requests that resulted in an error. 
          Calculated as (Number of Error Requests / Total Number of Calls) * 100.
        - 'average_duration' (float): The average response time of the requests in milliseconds within the time range. 
          Calculated as (Total Response Time / Total Number of Calls).
        - 'timeout_rate' (float): The average percentage of requests that timed out.
          Calculated as (Number of Timeout Requests / Total Number of Calls) * 100.
    """
    endpoint_data = explorer.query_endpoint_stats_in_range(endpoint, minute)
    return endpoint_data
