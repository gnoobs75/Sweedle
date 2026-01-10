"""
VRAM Diagnostic Tool

Checks VRAM usage at various stages to identify:
1. Normal Windows/driver baseline
2. PyTorch/CUDA overhead
3. Model memory usage
4. Potential memory leaks
"""

import logging
import gc
import sys
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def get_vram_info() -> Dict:
    """Get detailed VRAM information."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "error": "CUDA not available"}

        # Get memory stats
        allocated = torch.cuda.memory_allocated(0)
        reserved = torch.cuda.memory_reserved(0)
        total = torch.cuda.get_device_properties(0).total_memory

        # Get detailed memory stats if available
        try:
            stats = torch.cuda.memory_stats(0)
            peak_allocated = stats.get("allocated_bytes.all.peak", 0)
            num_allocs = stats.get("allocation.all.current", 0)
        except:
            peak_allocated = 0
            num_allocs = 0

        return {
            "available": True,
            "allocated_gb": allocated / 1e9,
            "reserved_gb": reserved / 1e9,
            "total_gb": total / 1e9,
            "free_gb": (total - allocated) / 1e9,
            "peak_allocated_gb": peak_allocated / 1e9,
            "num_allocations": num_allocs,
            "utilization_percent": (allocated / total) * 100,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def get_nvidia_smi_info() -> Dict:
    """Get VRAM info from nvidia-smi (includes all processes)."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            used_mb = int(parts[0])
            total_mb = int(parts[1])
            free_mb = int(parts[2])
            return {
                "available": True,
                "used_gb": used_mb / 1024,
                "total_gb": total_mb / 1024,
                "free_gb": free_mb / 1024,
                "source": "nvidia-smi (all processes)"
            }
    except Exception as e:
        return {"available": False, "error": str(e)}
    return {"available": False, "error": "nvidia-smi failed"}


def get_gpu_processes() -> List[Dict]:
    """Get list of processes using GPU."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        processes = []
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = [p.strip() for p in line.split(", ")]
                    if len(parts) >= 3:
                        processes.append({
                            "pid": parts[0],
                            "name": parts[1],
                            "memory_mb": int(parts[2]) if parts[2].isdigit() else 0
                        })
        return processes
    except Exception as e:
        return [{"error": str(e)}]


def analyze_pytorch_tensors() -> Dict:
    """Analyze PyTorch tensors currently in memory."""
    try:
        import torch

        # Count tensors by device
        cuda_tensors = []
        cpu_tensors = []

        for obj in gc.get_objects():
            try:
                if torch.is_tensor(obj):
                    size_mb = obj.element_size() * obj.nelement() / 1e6
                    if obj.is_cuda:
                        cuda_tensors.append({
                            "shape": tuple(obj.shape),
                            "dtype": str(obj.dtype),
                            "size_mb": size_mb,
                        })
                    else:
                        cpu_tensors.append({
                            "shape": tuple(obj.shape),
                            "dtype": str(obj.dtype),
                            "size_mb": size_mb,
                        })
            except:
                pass

        # Sort by size and get top 10
        cuda_tensors.sort(key=lambda x: x["size_mb"], reverse=True)

        return {
            "cuda_tensor_count": len(cuda_tensors),
            "cpu_tensor_count": len(cpu_tensors),
            "cuda_total_mb": sum(t["size_mb"] for t in cuda_tensors),
            "top_cuda_tensors": cuda_tensors[:10],
        }
    except Exception as e:
        return {"error": str(e)}


def check_module_caches() -> Dict:
    """Check for cached models in loaded modules."""
    caches_found = []

    try:
        for name, module in list(sys.modules.items()):
            if module is None:
                continue

            # Check for common cache patterns
            cache_attrs = ['_cache', 'cache', '_model', 'model', '_pipeline', 'pipeline']
            for attr in cache_attrs:
                if hasattr(module, attr):
                    obj = getattr(module, attr, None)
                    if obj is not None:
                        caches_found.append({
                            "module": name,
                            "attribute": attr,
                            "type": type(obj).__name__,
                        })

            # Check for hy3dgen specifically
            if 'hy3dgen' in name:
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        try:
                            attr = getattr(module, attr_name, None)
                            if hasattr(attr, 'to') and callable(getattr(attr, 'to', None)):
                                caches_found.append({
                                    "module": name,
                                    "attribute": attr_name,
                                    "type": type(attr).__name__,
                                    "has_cuda": "possibly"
                                })
                        except:
                            pass
    except Exception as e:
        return {"error": str(e)}

    return {"caches_found": caches_found, "count": len(caches_found)}


def full_diagnostic() -> Dict:
    """Run full VRAM diagnostic."""
    print("\n" + "="*60)
    print("VRAM DIAGNOSTIC REPORT")
    print("="*60)

    # 1. nvidia-smi view (all processes)
    print("\n[1] nvidia-smi (System-Wide VRAM Usage)")
    print("-" * 40)
    smi_info = get_nvidia_smi_info()
    if smi_info.get("available"):
        print(f"  Used:  {smi_info['used_gb']:.2f} GB")
        print(f"  Free:  {smi_info['free_gb']:.2f} GB")
        print(f"  Total: {smi_info['total_gb']:.2f} GB")
    else:
        print(f"  Error: {smi_info.get('error')}")

    # 2. GPU processes
    print("\n[2] Processes Using GPU")
    print("-" * 40)
    processes = get_gpu_processes()
    if processes and not processes[0].get("error"):
        for proc in processes:
            print(f"  PID {proc['pid']}: {proc['name']} - {proc['memory_mb']} MB")
        if not processes:
            print("  No compute processes found")
    else:
        print(f"  Could not query processes")

    # 3. PyTorch view
    print("\n[3] PyTorch CUDA Memory")
    print("-" * 40)
    pytorch_info = get_vram_info()
    if pytorch_info.get("available"):
        print(f"  Allocated: {pytorch_info['allocated_gb']:.2f} GB")
        print(f"  Reserved:  {pytorch_info['reserved_gb']:.2f} GB")
        print(f"  Peak:      {pytorch_info['peak_allocated_gb']:.2f} GB")
        print(f"  Active Allocations: {pytorch_info['num_allocations']}")
    else:
        print(f"  Error: {pytorch_info.get('error')}")

    # 4. Tensor analysis
    print("\n[4] PyTorch Tensor Analysis")
    print("-" * 40)
    tensor_info = analyze_pytorch_tensors()
    if not tensor_info.get("error"):
        print(f"  CUDA Tensors: {tensor_info['cuda_tensor_count']}")
        print(f"  CUDA Total:   {tensor_info['cuda_total_mb']:.1f} MB")
        if tensor_info['top_cuda_tensors']:
            print("  Top CUDA Tensors:")
            for t in tensor_info['top_cuda_tensors'][:5]:
                print(f"    - {t['shape']} ({t['dtype']}): {t['size_mb']:.1f} MB")
    else:
        print(f"  Error: {tensor_info.get('error')}")

    # 5. Module caches
    print("\n[5] Module Caches (Potential Leaks)")
    print("-" * 40)
    cache_info = check_module_caches()
    if not cache_info.get("error"):
        hy3dgen_caches = [c for c in cache_info['caches_found'] if 'hy3dgen' in c['module']]
        if hy3dgen_caches:
            print(f"  Found {len(hy3dgen_caches)} hy3dgen cached objects:")
            for c in hy3dgen_caches[:10]:
                print(f"    - {c['module']}.{c['attribute']} ({c['type']})")
        else:
            print("  No hy3dgen caches found")
    else:
        print(f"  Error: {cache_info.get('error')}")

    # 6. Baseline estimate
    print("\n[6] Baseline Analysis")
    print("-" * 40)
    if smi_info.get("available") and pytorch_info.get("available"):
        system_used = smi_info['used_gb']
        pytorch_allocated = pytorch_info['allocated_gb']
        other_usage = system_used - pytorch_allocated

        print(f"  Total System VRAM Used: {system_used:.2f} GB")
        print(f"  PyTorch Allocated:      {pytorch_allocated:.2f} GB")
        print(f"  Other (Windows/Apps):   {other_usage:.2f} GB")

        if other_usage > 3.0:
            print(f"\n  WARNING: High non-PyTorch usage ({other_usage:.1f} GB)")
            print("  This could be: Windows DWM, other apps, or driver overhead")

        if pytorch_allocated > 1.0 and tensor_info.get('cuda_tensor_count', 0) < 10:
            print(f"\n  WARNING: {pytorch_allocated:.1f} GB allocated but few tensors visible")
            print("  This suggests memory held by compiled CUDA kernels or cached models")

    print("\n" + "="*60)

    return {
        "nvidia_smi": smi_info,
        "processes": processes,
        "pytorch": pytorch_info,
        "tensors": tensor_info,
        "caches": cache_info,
    }


def clear_all_vram() -> Dict:
    """Attempt to clear all VRAM."""
    try:
        import torch

        before = get_vram_info()

        # 1. Python garbage collection
        gc.collect()
        gc.collect()
        gc.collect()

        # 2. Clear PyTorch cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

            # Try IPC collect if available
            if hasattr(torch.cuda, 'ipc_collect'):
                torch.cuda.ipc_collect()

            # Reset memory stats
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.reset_accumulated_memory_stats()

        after = get_vram_info()

        freed = before['allocated_gb'] - after['allocated_gb']

        return {
            "before_gb": before['allocated_gb'],
            "after_gb": after['allocated_gb'],
            "freed_gb": freed,
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    full_diagnostic()
