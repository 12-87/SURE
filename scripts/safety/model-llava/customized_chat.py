from typing import List
from omegaconf import OmegaConf
import torch

from mmte.utils.registry import registry
from mmte.utils.utils import get_abs_path
from mmte.models.llava.model.builder import load_pretrained_model
from mmte.models.llava.eval.run_llava import chat_model

from mmte.models.base import BaseChat, Response


@registry.register_chatmodel()
class CustomizedChat(BaseChat):
    """
    Chat class for llava model,
    the specific version is LLaVA-1.5 from https://github.com/haotian-liu/LLaVA.
    """

    # TODO: update model config
    MODEL_CONFIG = {
        "llava": 'customized-model.yaml',
    }
    model_family = list(MODEL_CONFIG.keys())

    def __init__(self, model_id: str, device: str="cuda:0"):
        super().__init__(model_id)
        self.device = device
        config = self.MODEL_CONFIG[self.model_id]
        self.config = OmegaConf.load(get_abs_path(config))

        self.model_name = self.config.model.model_name
        model_path = self.config.model.model_path

        self.tokenizer, self.model, self.image_processor, self.context_len = load_pretrained_model(
            model_path=model_path,
            model_base=None,
            model_name=self.model_name,    # get_model_name_from_path(model_path)
            device=self.device
        )

    @torch.no_grad()
    def chat(self, messages: List, **generation_kwargs):
        # TODO: if system message provided.
        assert len(messages) == 1, 'Only support one-turn conversation currently'
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

        if generation_kwargs.get("do_sample") == False:
            temperature = 0.0
            top_p = 1.0
        else:
            # TODO: set the default value
            temperature = generation_kwargs.get("temperature", 0.0)
            top_p = generation_kwargs.get("top_p", 1.0)

        args = type('Args', (), {
            "model_name": self.model_name,
            "query": user_message,
            "conv_mode": None,
            "image_file": image_path,
            "sep": ",",
            "temperature": temperature,
            "top_p": top_p,
            "num_beams": 1,
            "max_new_tokens": generation_kwargs.get("max_new_tokens", 1024),
            'dtype': torch.float16
        })()

        output_text = chat_model(self.tokenizer, self.model, self.image_processor, args)
        # print(output_text)
        scores = None
        
        return Response(self.model_id, output_text, scores, None)

