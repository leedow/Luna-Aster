"""
GPU 显存监控工具
用于在模型加载前后打印显存占用情况
"""

import torch
from loguru import logger
from typing import Dict, Optional


def get_gpu_memory_info(device: Optional[int] = None) -> Dict[str, float]:
    """
    获取 GPU 显存信息
    
    Args:
        device: GPU 设备索引，None 表示使用当前设备或默认设备
        
    Returns:
        Dict[str, float]: 包含显存信息的字典
            - allocated_mb: 已分配显存 (MB)
            - reserved_mb: 已保留显存 (MB)
            - total_mb: 总显存 (MB)
            - free_mb: 空闲显存 (MB)
    """
    if not torch.cuda.is_available():
        return {
            "allocated_mb": 0.0,
            "reserved_mb": 0.0,
            "total_mb": 0.0,
            "free_mb": 0.0,
            "available": False
        }
    
    if device is None:
        device = torch.cuda.current_device()
    
    # 获取显存统计
    allocated = torch.cuda.memory_allocated(device) / 1024**2  # MB
    reserved = torch.cuda.memory_reserved(device) / 1024**2  # MB
    total = torch.cuda.get_device_properties(device).total_memory / 1024**2  # MB
    free = total - reserved
    
    return {
        "allocated_mb": allocated,
        "reserved_mb": reserved,
        "total_mb": total,
        "free_mb": free,
        "available": True,
        "device": device
    }


def log_gpu_memory(stage: str, device: Optional[int] = None, model_name: str = ""):
    """
    打印 GPU 显存信息
    
    Args:
        stage: 阶段描述（如 "加载前", "加载后"）
        device: GPU 设备索引
        model_name: 模型名称
    """
    info = get_gpu_memory_info(device)
    
    if not info["available"]:
        logger.debug(f"💾 [{stage}] GPU 不可用")
        return
    
    device_name = f"GPU {info['device']}" if device is not None else "GPU"
    model_prefix = f"[{model_name}] " if model_name else ""
    
    logger.info(
        f"💾 {model_prefix}[{stage}] {device_name} 显存: "
        f"已分配={info['allocated_mb']:.2f}MB, "
        f"已保留={info['reserved_mb']:.2f}MB, "
        f"空闲={info['free_mb']:.2f}MB, "
        f"总计={info['total_mb']:.2f}MB"
    )


def get_memory_delta(before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
    """
    计算显存变化
    
    Args:
        before: 加载前的显存信息
        after: 加载后的显存信息
        
    Returns:
        Dict[str, float]: 显存变化
    """
    return {
        "allocated_delta_mb": after["allocated_mb"] - before["allocated_mb"],
        "reserved_delta_mb": after["reserved_mb"] - before["reserved_mb"],
        "free_delta_mb": after["free_mb"] - before["free_mb"]
    }

