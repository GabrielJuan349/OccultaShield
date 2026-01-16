import torch
import logging

logger = logging.getLogger('detection_module')

class GPUManager:
    """
    Singleton para gestionar recursos GPU.
    Detecta automáticamente la GPU y su VRAM disponible.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._refresh_info()
    
    def _refresh_info(self):
        if torch.cuda.is_available():
            self.device = "cuda"
            self.device_name = torch.cuda.get_device_name(0)
            self.vram_total_mb = torch.cuda.get_device_properties(0).total_memory // (1024**2)
            self.vram_free_mb = self._get_free_vram()
        else:
            self.device = "cpu"
            self.device_name = "CPU"
            self.vram_total_mb = 0
            self.vram_free_mb = 0
        
        logger.info(f"GPU Manager: {self.device_name}, VRAM: {self.vram_total_mb}MB")
    
    def _get_free_vram(self) -> int:
        if not torch.cuda.is_available():
            return 0
        torch.cuda.synchronize()
        allocated = torch.cuda.memory_allocated(0)
        total = torch.cuda.get_device_properties(0).total_memory
        return (total - allocated) // (1024**2)
    
    def can_fit_model(self, required_mb: int, safety_margin: float = 0.2) -> bool:
        """Verifica si hay suficiente VRAM para cargar un modelo"""
        if self.device == "cpu":
            return True
        available = self._get_free_vram()
        required_with_margin = int(required_mb * (1 + safety_margin))
        return available >= required_with_margin
    
    def get_strategy(self):
        """
        Determina la estrategia óptima según VRAM disponible.
        Optimizado para NVIDIA DGX Spark con batches grandes.
        Returns: (strategy, model_size, batch_size)
        """
        vram_gb = self.vram_total_mb / 1024
        
        if vram_gb < 8:
            logger.warning(f"Less than 8GB VRAM detected: {vram_gb:.0f}GB")
            return "sequential", "nano", 8  # Increased from 4
        elif vram_gb < 16:
            logger.warning(f"Less than 16GB VRAM detected: {vram_gb:.0f}GB")
            return "parallel", "small", 32  # Increased from 16
        elif vram_gb < 32:
            logger.warning(f"Less than 32GB VRAM detected: {vram_gb:.0f}GB")
            return "parallel", "medium", 64  # High VRAM
        else:  # 32GB+ (DGX Spark level)
            # Use maximum batch sizes for DGX Spark
            batch = min(128, int(vram_gb * 3))  # Up to 128 frames per batch
            logger.info(f"🚀 DGX Spark mode: {vram_gb:.0f}GB VRAM, batch_size={batch}")
            return "parallel", "medium", batch

# Instancia global
gpu_manager = GPUManager()
