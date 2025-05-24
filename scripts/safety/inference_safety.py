import os
import csv
import json
import random
import argparse
from mmte.utils.registry import registry
from model.customized_chat import CustomizedChat
from openai import OpenAI

from const import *

def random_shuffle_sentence(sentence):
    ssp = sentence.split()
    random.shuffle(ssp)
    return ssp

def infer_and_save(input_folder_path, csv_output_path, json_output_path, prompts_dict, attack, model):
    results = []

    for sub_folder in os.listdir(input_folder_path):
        sub_folder_path = os.path.join(input_folder_path, sub_folder)
        if not os.path.isdir(sub_folder_path):
            continue

        json_file_path = os.path.join(sub_folder_path, "data.json")
        if not os.path.exists(json_file_path):
            print(f"data.json not found in {sub_folder_path}, skipping.")
            continue

        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data_info = json.load(json_file)

        if attack == "figstep" and "safebench" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_figstep")
            image_ext = ".png"
            get_question1 = lambda item: prompts_dict['figstep_prompt']
        elif attack == "mmsafetybench" and "safebench" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_qr")
            image_ext = ".jpg"
            get_question1 = lambda item: item.get("qr_prompt", "")
        elif attack == "hades" and "hades" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images")
            image_ext = ".jpg"
            get_question1 = lambda item: item.get("hades_prompt", "")
        elif attack == "mml_wr" and "hades" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_wr")
            image_ext = ".jpg"
            get_question1 = lambda item: prompts_dict['wr_game_prompt'].format(item["replace_map"], random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_mirror" and "hades" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_mirror")
            image_ext = ".jpg"
            get_question1 = lambda item: prompts_dict['mirror_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_base64" and "hades" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_base64")
            image_ext = ".jpg"
            get_question1 = lambda item: prompts_dict['base64_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_rotate" and "hades" in input_folder_path:
            images_folder = os.path.join(sub_folder_path, "images_rotate")
            image_ext = ".jpg"
            get_question1 = lambda item: prompts_dict['rotate_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_wr":
            images_folder = os.path.join(sub_folder_path, "images_wr")
            image_ext = ".png"
            get_question1 = lambda item: prompts_dict['wr_game_prompt'].format(item["replace_map"], random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_mirror":
            images_folder = os.path.join(sub_folder_path, "images_mirror")
            image_ext = ".png"
            get_question1 = lambda item: prompts_dict['mirror_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_base64":
            images_folder = os.path.join(sub_folder_path, "images_base64")
            image_ext = ".png"
            get_question1 = lambda item: prompts_dict['base64_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        elif attack == "mml_rotate":
            images_folder = os.path.join(sub_folder_path, "images_rotate")
            image_ext = ".png"
            get_question1 = lambda item: prompts_dict['rotate_game_prompt'].format(random_shuffle_sentence(item["original_prompt"]))
        else:
            print(f"Unsupported input_folder_path and attack combination: {input_folder_path}, {attack}")
            continue

        if not os.path.exists(images_folder):
            print(f"{images_folder} not found, skipping.")
            continue

        for item in data_info:
            image_name = f"{item['id']}{image_ext}"
            image_path = os.path.join(images_folder, image_name)
            if not os.path.exists(image_path):
                print(f"Image {image_name} not found in {images_folder}, skipping.")
                continue

            question1 = get_question1(item)
            question2 = item.get("original_prompt", "")

            if not question1:
                print(f"No question1 for image {image_name}, skipping.")
                continue
            if not question2:
                print(f"No question2 for image {image_name}, skipping.")
                continue

            inputs = [{
                "role": "user",
                "content": {"text": question1, "image_path": image_path}
            }]

            try:
                response = model.chat(inputs, do_sample=False)
                model_answer = response.content if response else "No response"

                result = {
                    'question': question2,
                    'image_path': image_path,
                    'model_answer': model_answer,
                    'prompt': question1
                }
                results.append(result)

                with open(csv_output_path, mode='a', newline='', encoding='utf-8') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=["question", "image_path", "model_answer", "prompt"])
                    if os.path.getsize(csv_output_path) == 0:
                        writer.writeheader()
                    writer.writerow(result)

            except Exception as e:
                print(f"Error processing image: {image_name}")
                print(e)

    with open(json_output_path, mode='w', encoding='utf-8') as json_file:
        json.dump(results, json_file, indent=4, ensure_ascii=False)

    print(f"Results saved to {csv_output_path} and {json_output_path}")

def main():
    parser = argparse.ArgumentParser(description="Run inference on safebench WR dataset")
    parser.add_argument('--input_folder_path', type=str, required=True, help='Input folder path')
    parser.add_argument('--csv_output_path', type=str, required=True, help='CSV output file path')
    parser.add_argument('--json_output_path', type=str, required=True, help='JSON output file path')
    parser.add_argument('--attack', type=str, required=True, help='figstep, mmsafetybench, hades, mml_wr, mml_mirror, mml_base64, mml_rotate')

    args = parser.parse_args()

    model_id = "deepseek"
    print("Successful Register:", model_id in registry.list_chatmodels())
    if model_id not in registry.list_chatmodels():
        print(f"Your model is not correctly registered as {model_id}")
        exit(0)

    print("Loading Model...")
    try:
        model = registry.get_chatmodel_class(model_id)(model_id)
    except Exception as e:
        print(e)
        print("Model cannot be successfully loaded.")
        exit(0)
    print("Model successfully loaded.")

    prompts_dict = {
        "wr_game_prompt": wr_game_prompt,
        "mirror_game_prompt": mirror_game_prompt,
        "base64_game_prompt": base64_game_prompt,
        "rotate_game_prompt": rotate_game_prompt,
        "figstep_prompt": figstep_prompt,
        "static_defense_pre": static_defense_pre,
    }

    with open(args.csv_output_path, mode='w', encoding='utf-8') as f:
        pass

    infer_and_save(args.input_folder_path, args.csv_output_path, args.json_output_path, prompts_dict, args.attack, model)

if __name__ == "__main__":
    main()
