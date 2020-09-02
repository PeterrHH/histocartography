#!/usr/bin/env python3
"""
Script for generating explanations
"""

import importlib
import torch
import mlflow
import numpy as np
from tqdm import tqdm 
import torch

from histocartography.utils.io import read_params, write_json, complete_path
from histocartography.dataloader.pascale_dataloader import make_data_loader
from histocartography.ml.models.constants import AVAILABLE_MODEL_TYPES, MODEL_TYPE
from histocartography.interpretability.constants import AVAILABLE_EXPLAINABILITY_METHODS, INTERPRETABILITY_MODEL_TYPE_TO_LOAD_FN
from histocartography.utils.arg_parser import parse_arguments
from histocartography.ml.models.constants import load_superpx_graph, load_cell_graph
from histocartography.utils.io import get_device, flatten_dict
from histocartography.dataloader.constants import get_label_to_tumor_type
from histocartography.interpretability.meta_explanation import MetaGraphExplanation


# flush warnings
import warnings
warnings.filterwarnings("ignore")

# cuda support
CUDA = torch.cuda.is_available()
DEVICE = get_device(CUDA)



def main(args):
    """
    Train HistoGraph.
    Args:
        args (Namespace): parsed arguments.
    """

    # load config file
    config = read_params(args.config_fpath, verbose=True)

    # constants
    label_to_tumor_type = get_label_to_tumor_type(config['model_params']['class_split'])

    # extract interpretability model type
    interpretability_model_type = config['explanation_params']['explanation_type']

    # make data loaders
    dataloaders, input_feature_dims = make_data_loader(
        batch_size=1,
        num_workers=args.number_of_workers,
        path=args.data_path,
        config=config,
        class_split=config['model_params']['class_split'],
        cuda=CUDA,
        load_cell_graph=load_cell_graph(config['model_type']),
        load_superpx_graph=load_superpx_graph(config['model_type']),
        load_image=True,
        load_nuclei_seg_map=load_cell_graph(config['model_type']),
        load_superpx_map=load_superpx_graph(config['model_type']),
        fold_id=0
    )

    # append dataset info to config
    config['data_params'] = {}
    config['data_params']['input_feature_dims'] = input_feature_dims
    config['explanation_params']['model_params']['class_split'] = config['model_params']['class_split']
    config['explanation_params']['model_params']['model_type'] = config['model_type']

    # define GNN model
    if interpretability_model_type in list(AVAILABLE_EXPLAINABILITY_METHODS.keys()):
        module = importlib.import_module('histocartography.utils.io')
        model = getattr(module, INTERPRETABILITY_MODEL_TYPE_TO_LOAD_FN[interpretability_model_type])(config)
        if CUDA:
            model = model.cuda()
    else:
        raise ValueError(
            'Model: {} not recognized. Options are: {}'.format(
                model_type, list(AVAILABLE_EXPLAINABILITY_METHODS.keys())
            )
        )

    # define interpretability model 
    if interpretability_model_type in list(AVAILABLE_EXPLAINABILITY_METHODS.keys()):
        module = importlib.import_module(
            'histocartography.interpretability.{}'.format(interpretability_model_type)
        )
        interpretability_model = getattr(
            module, AVAILABLE_EXPLAINABILITY_METHODS[interpretability_model_type])(
                model, config['explanation_params'], CUDA
            )
    else:
        raise ValueError(
            'Interpretability method: {} not recognized. Options are: {}'.format(
                interpretability_model_type, list(AVAILABLE_EXPLAINABILITY_METHODS.keys())
            )
        )

    # mlflow log parameters
    inter_config = flatten_dict(config['explanation_params'])
    for key, val in inter_config.items():
        mlflow.log_param(key, val)

    # explain instance from the train set
    counter = 0
    all_explanations = []
    for data, label in tqdm(dataloaders[args.split]):

        explanation = interpretability_model.explain(
            data=data,
            label=label
        )
        
        if counter % 3 == 0:
            torch.cuda.empty_cache() 

        explanation.write()
        all_explanations.append(explanation)
        counter += 1

    # wrap all the explanations in object and write 
    meta_explanation = MetaGraphExplanation(config['explanation_params'], all_explanations)
    meta_explanation.write()


if __name__ == "__main__":
    main(args=parse_arguments())
