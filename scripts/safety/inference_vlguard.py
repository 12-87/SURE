import os
import json
import torch
import csv
from PIL import Image
from mmte.utils.registry import registry
from model.customized_chat import CustomizedChat

model_id = "deepseek"

print("Successful Register:", model_id in registry.list_chatmodels())

if model_id not in registry.list_chatmodels():
    print("Your model is not correctly registered as", model_id)
    exit(0)

print("Loading Model...")
try:
    model = registry.get_chatmodel_class(model_id)(model_id)
except Exception as e:
    print(e)
    print("Model cannot be successfully loaded.")
    exit(0)
print("Model successfully loaded.")

print("-----------------------------------------")
print("Calculating the total numbers...")

variables = vars(model)
param_names = []
for k, v in variables.items():
    if isinstance(v, torch.nn.Module):
        param_names.append(k)
total_params = sum(sum(param.numel() for param in getattr(model, k).parameters()) for k in param_names)
print(f"Total Params: {total_params / (10**9)}B")
print("-----------------------------------------")

def infer_and_save_from_json(json_file, safe_safe_output_path, safe_unsafe_output_path, unsafe_unsafe_output_path):
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    safe_safe_results = []
    safe_unsafe_results = []
    unsafe_unsafe_results = []
    
    safe_safe_idx = 0
    safe_unsafe_idx = 0
    unsafe_unsafe_idx = 0
    idx = 0

    for item in data:
        question = item.get("question", "")
        image_path = item.get("image_path", "")
        category = item.get("category", "")
        idx += 1

        if not image_path:
            print(f"No image found for question: {question}")
            continue

        try:
            print(f"Processing {idx} image: {image_path} - Category: {category}")

            inputs = [{"role": "user", "content": {"text": question, "image_path": image_path}}]

            response = model.chat(inputs, do_sample=False)

            result = {
                "question": question,
                "answer": response.content,
                "image_path": image_path
            }

            if category == "safe-safe":
                safe_safe_results.append(result)
                safe_safe_idx += 1
            elif category == "safe-unsafe":
                safe_unsafe_results.append(result)
                safe_unsafe_idx += 1
            elif category == "unsafe-unsafe":
                unsafe_unsafe_results.append(result)
                unsafe_unsafe_idx += 1

            print(question)
            print(response.content)

        except Exception as e:
            print(f"Error processing image: {image_path}")
            print(e)

    with open(safe_safe_output_path, 'w', encoding='utf-8') as file:
        json.dump(safe_safe_results, file, ensure_ascii=False, indent=4)
    print(f"Safe-Safe results saved to {safe_safe_output_path}")

    with open(safe_unsafe_output_path, 'w', encoding='utf-8') as file:
        json.dump(safe_unsafe_results, file, ensure_ascii=False, indent=4)
    print(f"Safe-Uunsafe results saved to {safe_unsafe_output_path}")

    with open(unsafe_unsafe_output_path, 'w', encoding='utf-8') as file:
        json.dump(unsafe_unsafe_results, file, ensure_ascii=False, indent=4)
    print(f"Unsafe-Uunsafe results saved to {unsafe_unsafe_output_path}")


json_input_path = 'vlguard.json'
safe_safe_output_path = 'safe_safe.json'
safe_unsafe_output_path = 'safe_unsafe.json'
unsafe_unsafe_output_path = 'unsafe_unsafe.json'

infer_and_save_from_json(json_input_path, safe_safe_output_path, safe_unsafe_output_path, unsafe_unsafe_output_path)
