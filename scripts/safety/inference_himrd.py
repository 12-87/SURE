import os
import csv
import json
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

def infer_and_save(txt_file_path, image_folder_path, csv_output_path, json_output_path):
    results = []

    with open(csv_output_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["question", "image_path", "model_answer", "prompt"])
        writer.writeheader()
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            questions = txt_file.readlines()

        for idx, question in enumerate(questions):
            image_name = f"{idx:05d}.png"
            image_path = os.path.join(image_folder_path, image_name)
            if not os.path.exists(image_path):
                print(f"Image {image_name} not found in {image_folder_path}, skipping.")
                continue
            question = question.strip()
            if not question:
                print(f"Empty question for image {image_name}, skipping.")
                continue

            inputs = [{
                "role": "user", 
                "content": {"text": question, "image_path": image_path}
            }]

            try:
                response = model.chat(inputs, do_sample=False)
                model_answer = response.content if response else "No response"
                result = {
                    'question': question,
                    'image_path': image_path,
                    'model_answer': model_answer,
                    'prompt': question
                }
                writer.writerow(result)
                results.append(result)

            except Exception as e:
                print(f"Error processing image: {image_name}")
                print(e)

    with open(json_output_path, mode='w', encoding='utf-8') as json_file:
        json.dump(results, json_file, indent=4, ensure_ascii=False)

    print(f"Results saved to {csv_output_path} and {json_output_path}")

# 运行推理函数
txt_file_path = 'final_prompts.txt'
image_folder_path = 'final_images'
csv_output_path = 'himrd.csv'
json_output_path = 'himrd.json'

infer_and_save(txt_file_path, image_folder_path, csv_output_path, json_output_path)
