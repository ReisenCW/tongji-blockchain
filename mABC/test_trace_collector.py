"""
测试 TraceExplorer (trace_collect.py) 功能
测试依赖关系查询和范围查询是否正常工作
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from handle.trace_collect import TraceExplorer

def test_get_endpoint_downstream():
    """测试单个时间点的端点下游依赖查询"""
    print("=" * 60)
    print("测试 1: 查询单个时间点的端点下游依赖")
    print("=" * 60)
    
    explorer = TraceExplorer()
    
    # 测试用例 1: train-buy 的下游依赖
    endpoint = "train-buy"
    time = "2023-10-15 14:00:00"
    
    print(f"\n查询端点: {endpoint}")
    print(f"时间: {time}")
    
    result = explorer.get_endpoint_downstream(endpoint, time)
    
    if result:
        print("✓ 查询成功！")
        print(f"  下游端点列表: {result}")
        print(f"  下游端点数量: {len(result)}")
    else:
        print("✓ 查询成功（无下游依赖）")
    
    # 测试用例 2: None（顶层端点）
    endpoint2 = "None"
    time2 = "2023-10-15 14:00:00"
    
    print(f"\n查询端点: {endpoint2} (顶层入口)")
    print(f"时间: {time2}")
    
    result = explorer.get_endpoint_downstream(endpoint2, time2)
    
    if result:
        print("✓ 查询成功！")
        print(f"  顶层端点列表: {result}")
        print(f"  顶层端点数量: {len(result)}")
    else:
        print("✓ 查询成功（无依赖）")
    
    # 测试用例 3: train-cancel 的下游依赖
    endpoint3 = "train-cancel"
    time3 = "2023-10-15 14:01:00"
    
    print(f"\n查询端点: {endpoint3}")
    print(f"时间: {time3}")
    
    result = explorer.get_endpoint_downstream(endpoint3, time3)
    
    if result:
        print("✓ 查询成功！")
        print(f"  下游端点列表: {result}")
        print(f"  下游端点数量: {len(result)}")
    else:
        print("✓ 查询成功（无下游依赖）")
    
    return True

def test_get_endpoint_downstream_in_range():
    """测试时间范围内的端点下游依赖查询"""
    print("\n" + "=" * 60)
    print("测试 2: 查询时间范围内的端点下游依赖")
    print("=" * 60)
    
    explorer = TraceExplorer()
    
    endpoint = "train-buy"
    time = "2023-10-15 14:00:00"
    
    print(f"\n查询端点: {endpoint}")
    print(f"中心时间: {time}")
    print(f"范围: 前15分钟 到 后5分钟")
    
    result = explorer.get_endpoint_downstream_in_range(endpoint, time)
    
    if result:
        print(f"✓ 查询成功！返回 {len(result)} 个时间点的数据")
        
        # 只显示有数据的时间点
        has_data_count = sum(1 for v in result.values() if v)
        print(f"  有效数据点: {has_data_count}")
        
        print("\n有下游依赖的时间点:")
        count = 0
        for time_str, downstream_list in result.items():
            if downstream_list:
                print(f"  [{time_str}] → {downstream_list}")
                count += 1
                if count >= 5:  # 只显示前5个
                    break
        
        if count == 0:
            print("  (在查询范围内没有找到下游依赖数据)")
    else:
        print("✗ 查询失败：返回空结果")
    
    return True

def test_dependency_chain():
    """测试完整的依赖链路"""
    print("\n" + "=" * 60)
    print("测试 3: 追踪完整的依赖调用链")
    print("=" * 60)
    
    explorer = TraceExplorer()
    
    time = "2023-10-15 14:00:00"
    
    print(f"\n时间: {time}")
    print("依赖链路追踪:")
    
    # 从顶层开始
    chain = []
    current = "None"
    level = 0
    
    while True:
        downstream = explorer.get_endpoint_downstream(current, time)
        
        if current == "None":
            print(f"  {'  ' * level}[顶层入口]")
        else:
            print(f"  {'  ' * level}└─ {current}")
        
        if not downstream:
            break
        
        # 只追踪第一个下游端点
        current = downstream[0] if isinstance(downstream, list) else downstream
        chain.append(current)
        level += 1
        
        if level > 10:  # 防止无限循环
            print("  (链路过长，停止追踪)")
            break
    
    print(f"\n✓ 依赖链路深度: {level} 层")
    print(f"  完整路径: None → {' → '.join(chain)}")
    
    return True

def test_nonexistent_endpoint():
    """测试查询不存在的端点"""
    print("\n" + "=" * 60)
    print("测试 4: 查询不存在的端点（边界情况）")
    print("=" * 60)
    
    explorer = TraceExplorer()
    
    endpoint = "nonexistent-endpoint"
    time = "2023-10-15 14:00:00"
    
    print(f"\n查询端点: {endpoint}")
    print(f"时间: {time}")
    
    result = explorer.get_endpoint_downstream(endpoint, time)
    
    if not result:
        print("✓ 正确处理：返回空/空列表（预期行为）")
    else:
        print("✗ 意外结果：应该返回空")
    
    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TraceExplorer 功能测试")
    print("=" * 60)
    
    try:
        test_get_endpoint_downstream()
        test_get_endpoint_downstream_in_range()
        test_dependency_chain()
        test_nonexistent_endpoint()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
