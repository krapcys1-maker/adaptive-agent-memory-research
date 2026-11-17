# -*- coding: utf-8 -*-
"""
    ### Verify GPU Connection
    Run the cell below to check if the T4 GPU is successfully attached and view its specifications.
"""

import time
import torch
import gc
from sentence_transformers import SentenceTransformer

# List of all models to benchmark
models = [
    "Qwen/Qwen3-Embedding-4B",
    "Qwen/Qwen3-Embedding-0.6B",
    "BAAI/bge-small-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2"
]

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}\n")

# A sample text string simulating an agent's step observation
dummy_text = "The agent observes the current state of the environment. " * 11

for model_id in models:
    print(f"--- Testing {model_id} ---")
    
    # Reset peak memory stats before loading the model
    if device == 'cuda':
        torch.cuda.reset_peak_memory_stats()
        
    # Load model in fp16 to match the owner's methodology
    model = SentenceTransformer(model_id, device=device, model_kwargs={"torch_dtype": torch.float16})
    
    # 1. Warm-up (10 iterations)
    with torch.no_grad():
        for _ in range(10):
            _ = model.encode(dummy_text, convert_to_tensor=True)
            
    if device == 'cuda':
        torch.cuda.synchronize() 
        
    # 2. Measure Latency (100 iterations for a stable mean average)
    num_iterations = 100
    start_time = time.time()
    
    with torch.no_grad():
        for _ in range(num_iterations):
            _ = model.encode(dummy_text, convert_to_tensor=True)
            
    if device == 'cuda':
        torch.cuda.synchronize()
        
    end_time = time.time()
    latency_ms = ((end_time - start_time) / num_iterations) * 1000
    
    # 3. Measure Peak VRAM
    if device == 'cuda':
        peak_vram = torch.cuda.max_memory_allocated() / (1024 ** 3)
    else:
        peak_vram = 0.0
        
    print(f"Peak GPU VRAM Usage: {peak_vram:.2f} GB")
    print(f"GPU Latency: {latency_ms:.2f} ms per step")
    
    # 4. Strict Cleanup to free VRAM for the next model
    del model
    gc.collect()
    if device == 'cuda':
        torch.cuda.empty_cache()
    print(f"VRAM after cleanup: {torch.cuda.memory_allocated() / (1024 ** 3):.2f} GB\n")

print("Benchmarking complete.")
