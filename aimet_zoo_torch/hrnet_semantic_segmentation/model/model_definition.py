#!/usr/bin/env python3
# -*- mode: python -*-
# pylint: disable=E0401,E1101,W0621,R0915,R0914,R0912,W0212
# =============================================================================
#  @@-COPYRIGHT-START-@@
#
#  Copyright (c) 2022 of Qualcomm Innovation Center, Inc. All rights reserved.
#
#  @@-COPYRIGHT-END-@@
# =============================================================================

""" HRNet Semantic Segmentation """

import json
import os
import pathlib
import torch
from aimet_torch.quantsim import QuantizationSimModel, load_encodings_to_sim
from aimet_torch.cross_layer_equalization import equalize_model
from aimet_zoo_torch.common.downloader import Downloader
from aimet_zoo_torch.hrnet_semantic_segmentation.model.models.seg_hrnet import (
    get_seg_model,
)
from aimet_zoo_torch.hrnet_semantic_segmentation.model.config import (
    default,
    hrnet_config,
)


class HRNetSemSeg(Downloader):
    """HRNET-w48 Semantic Segmentation parent class with automated loading of weights and providing a QuantSim with pre-computed encodings"""

    def __init__(self, model_config=None):
        """
        :param model_config:             named model config from which to obtain model artifacts and arguments.
                                         If provided, overwrites the other arguments passed to this object
        """
        parent_dir = str(pathlib.Path(os.path.abspath(__file__)).parent)
        self.cfg = False
        if model_config:
            config_filepath = parent_dir + "/model_cards/" + model_config + ".json"
            if os.path.exists(config_filepath):
                with open(config_filepath) as f_in:
                    self.cfg = json.load(f_in)
        if self.cfg:
            Downloader.__init__(
                self,
                url_pre_opt_weights=self.cfg["artifacts"]["url_pre_opt_weights"],
                url_post_opt_weights=self.cfg["artifacts"]["url_post_opt_weights"],
                url_adaround_encodings=self.cfg["artifacts"]["url_adaround_encodings"],
                url_aimet_encodings=self.cfg["artifacts"]["url_aimet_encodings"],
                url_aimet_config=self.cfg["artifacts"]["url_aimet_config"],
                model_dir=parent_dir,
                model_config=model_config,
            )
            self.input_shape = tuple(
                x if x is not None else 1 for x in self.cfg["input_shape"]
            )
        default._C.MODEL.EXTRA = hrnet_config.HRNET_48
        self.model = get_seg_model(default._C, is_train=False)

    def from_pretrained(self, quantized=False):
        """load pretrained weights"""
        if not self.cfg:
            raise NotImplementedError(
                "There are no pretrained weights available for the model_config passed"
            )
        self._download_pre_opt_weights()
        self._download_post_opt_weights()
        self._download_aimet_config()
        self._download_aimet_encodings()
        self._download_adaround_encodings()
        if quantized:
            equalize_model(self.model, self.input_shape)
            state_dict = torch.load(self.path_post_opt_weights)
            self.model.load_state_dict(state_dict)
            self.model.cuda()
        else:
            state_dict = torch.load(self.path_pre_opt_weights)
            self.model.load_state_dict(state_dict)
            self.model.cuda()
        self.model.eval()

    def get_quantsim(self, quantized=False):
        """get quantsim object with pre-loaded encodings"""
        if not self.cfg:
            raise NotImplementedError(
                "There is no Quantization Simulation available for the model_config passed"
            )
        if quantized:
            self.from_pretrained(quantized=True)
        else:
            self.from_pretrained(quantized=False)
        device = torch.device("cuda")
        dummy_input = torch.rand(self.input_shape, device=device)
        kwargs = {
            "quant_scheme": self.cfg["optimization_config"][
                "quantization_configuration"
            ]["quant_scheme"],
            "default_param_bw": self.cfg["optimization_config"][
                "quantization_configuration"
            ]["param_bw"],
            "default_output_bw": self.cfg["optimization_config"][
                "quantization_configuration"
            ]["output_bw"],
            "config_file": self.path_aimet_config,
            "dummy_input": dummy_input,
        }
        sim = QuantizationSimModel(self.model, **kwargs)
        if self.path_aimet_encodings and quantized:
            load_encodings_to_sim(sim, self.path_aimet_encodings)
            print("load_encodings_to_sim finished!")
        if self.path_adaround_encodings and quantized:
            sim.set_and_freeze_param_encodings(self.path_adaround_encodings)
            print("set_and_freeze_param_encodings finished!")
        sim.model.eval()
        return sim
