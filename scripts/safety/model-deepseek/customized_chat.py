import torch
from typing import List
from transformers import AutoModelForCausalLM
from mmte.utils.registry import registry
from mmte.models.base import BaseChat, Response
from checkpoint.deepseek_vl.models.processing_vlm import VLChatProcessor
from checkpoint.deepseek_vl.models.modeling_vlm import MultiModalityCausalLM
from checkpoint.deepseek_vl.utils.io import load_pil_images
# import gradio as gr


@registry.register_chatmodel()
class CustomizedChat(BaseChat):
    """
    Chat class for deepseek-7b model,
    """

    # TODO: update model config
    MODEL_CONFIG = {
        "deepseek": 'model/customized-model.yaml',
    }
    model_family = list(MODEL_CONFIG.keys())

    def __init__(self, model_id: str, device: str="cuda:0"):
        super().__init__(model_id)
        model_path = "deepseek-vl-7b-chat"
        
        vl_chat_processor: VLChatProcessor = VLChatProcessor.from_pretrained(model_path)
        tokenizer = vl_chat_processor.tokenizer

        vl_gpt: MultiModalityCausalLM = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True)
        vl_gpt = vl_gpt.to(torch.bfloat16).to(device).eval()
        
        self.device = device
        self.model = vl_gpt
        self.tokenizer = tokenizer
        self.vl_chat_processor = vl_chat_processor


    @torch.no_grad()
    def chat(self, messages: List, **generation_kwargs):
        # TODO: if system message provided.
        for message in messages:
            if message["role"] in ["system", "user", "assistant"]:
                if message["role"] == "user":
                    if isinstance(message["content"], dict):
                        # multimodal
                        image_path = message["content"]["image_path"]
                        user_message = message["content"]["text"]
                    else:
                        image_path = None
                        user_message = message["content"]
                elif message["role"] == "assistant":
                    # TODO: add assistant answer into the conversation
                    pass
            else:
                raise ValueError("Unsupported role. Only system, user and assistant are supported.")

        if image_path is not None:
            conversation = [
                {
                    "role": "User",
                    "content": "<image_placeholder>" + user_message,
                    "images": [image_path]
                },
                {
                    "role": "Assistant",
                    "content": ""
                }
            ]
        else:
            conversation = [
                {
                    "role": "User",
                    "content": user_message,
                },
                {
                    "role": "Assistant",
                    "content": ""
                }
            ]

        pil_images = load_pil_images(conversation)
        prepare_inputs = self.vl_chat_processor(
            conversations=conversation,
            images=pil_images,
            force_batchify=True
        ).to(self.model.device)

        # run image encoder to get the image embeddings
        inputs_embeds = self.model.prepare_inputs_embeds(**prepare_inputs)

        # run the model to get the response
        outputs = self.model.language_model.generate(
            inputs_embeds=inputs_embeds,
            attention_mask=prepare_inputs.attention_mask,
            pad_token_id=self.tokenizer.eos_token_id,
            bos_token_id=self.tokenizer.bos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            max_new_tokens=generation_kwargs.get("max_new_tokens", 1024),
            do_sample=generation_kwargs.get("do_sample"),
            use_cache=True
        )

        output_text = self.tokenizer.decode(outputs[0].cpu().tolist(), skip_special_tokens=True)

        scores = None
        return Response(self.model_id, output_text, scores, None)