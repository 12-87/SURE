import os
import csv
import json
from PIL import Image
from mmte.utils.registry import registry
from model.customized_chat import CustomizedChat
from openai import OpenAI

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

def infer_and_save(json_file_path, image_folder_path, csv_output_path, json_output_path):
    results = []

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data_info = json.load(f)

    with open(csv_output_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
            "question_id", "image_path", "question", "category", 
            "options", "correct_option", "response_mcqa"
        ])
        writer.writeheader()

        for item in data_info:
            question_id = item.get("question_id")
            image_name = item.get("image")
            question = item.get("question")
            category = item.get("category")
            correct_option = item.get("correct_option")
            options_dict = item.get("options", {})
            options = "\n".join([f"({key}) {value}" for key, value in options_dict.items()])

            if not (question_id and image_name and question):
                print(f"Missing fields in entry {item}, skipping.")
                continue

            image_path = os.path.join(image_folder_path, image_name)
            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}, skipping.")
                continue

            prompt = f"""
            Answer the following multi-choice questions with the option's letter directly.

            Qusetion: {question}
            Option:
            {options}

            Chocie:
            """

            inputs = [{
                "role": "user",
                "content": {
                    "text": prompt,
                    "image_path": image_path
                }
            }]

            try:
                model_answer = model.chat(inputs, do_sample=False)
                response = model_answer.content if model_answer else "No response"

                result = {
                    "question_id": question_id,
                    "image_path": image_path,
                    "question": question,
                    "category": category,
                    "options": options,
                    "correct_option": correct_option,
                    "response_mcqa": response
                }
                results.append(result)
                writer.writerow(result)

            except Exception as e:
                print(f"Error processing {image_name}: {e}")
                continue

    # 保存 JSON 结果
    with open(json_output_path, 'w', encoding='utf-8') as jf:
        json.dump(results, jf, indent=4, ensure_ascii=False)

    print(f"Results saved to: {csv_output_path} and {json_output_path}")

json_file_path = 'siuo_mcqa.json'
image_folder_path = 'images'
csv_output_path = 'siuo.csv'
json_output_path = 'siuo.json'

infer_and_save(json_file_path, image_folder_path, csv_output_path, json_output_path)