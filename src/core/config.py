import os
import time
import yaml
import shutil
import argparse
import operator
import itertools
from os.path import join
from loguru import logger
from functools import reduce
from yacs.config import CfgNode as CN
from typing import Dict, List, Union, Any
from flatten_dict import flatten, unflatten

##### CONSTANTS #####
DATASET_HOME = ''
H36M_ROOT = join(DATASET_HOME, 'h36m')
COCO_ROOT = join(DATASET_HOME, 'coco')
MPI_INF_3DHP_ROOT = join(DATASET_HOME, 'mpi_inf_3dhp')
PW3D_ROOT = join(DATASET_HOME, '3dpw')
MPII_ROOT = join(DATASET_HOME, 'mpii')
LSP_ROOT = join(DATASET_HOME, 'lsp')
LSP_ORIGINAL_ROOT = join(DATASET_HOME, 'lsp_original')
LSPET_ROOT = join(DATASET_HOME, 'hr-lspet')
OCHUMAN_ROOT = join(DATASET_HOME, 'OCHuman')
D3OH_ROOT = join(DATASET_HOME, '3doh')

CONFIG_HOME = ''
DATASET_NPZ_PATH = join(CONFIG_HOME, 'dataset_extras')
JOINT_REGRESSOR_TRAIN_EXTRA = join(CONFIG_HOME, 'J_regressor_extra.npy')
JOINT_REGRESSOR_H36M = join(CONFIG_HOME, 'J_regressor_h36m.npy')
SMPL_MEAN_PARAMS = join(CONFIG_HOME, 'smpl_mean_params.npz')
SMPL_MODEL_DIR = join(CONFIG_HOME, 'smpl')
STATIC_FITS_DIR = join(CONFIG_HOME, 'static_fits')

OPENPOSE_PATH = None

DATASET_FOLDERS = {
    'coco': COCO_ROOT,
    'coco3d': COCO_ROOT,
    'cocoall3d': COCO_ROOT,

    'mpii': MPII_ROOT,

    'lsp': LSP_ROOT,
    'lsp-orig': LSP_ORIGINAL_ROOT,
    'lspet': LSPET_ROOT,

    'ochuman': OCHUMAN_ROOT,
    'ochuman-val': OCHUMAN_ROOT,

    '3doh': D3OH_ROOT,
    
    'h36m': H36M_ROOT,
    'h36m-p1': H36M_ROOT,
    'h36m-p2': H36M_ROOT,

    '3dpw': PW3D_ROOT,
    '3dpw-val': PW3D_ROOT,

    'mpi-inf-3dhp': MPI_INF_3DHP_ROOT,
    'mpi-inf-3dhp_val': MPI_INF_3DHP_ROOT,
}

DATASET_FILES = [
    {
        'h36m-p1': 'h36m_valid_protocol1.npz',
        'h36m-p2': 'h36m_valid_protocol2.npz',
        'mpi-inf-3dhp': 'mpi_inf_3dhp_valid.npz',
        '3dpw': '3dpw_test_with_mmpose.npz',
        'ochuman': 'ochuman_test_eft.npz',
        'lspet': 'lspet_test_eft.npz',
        '3doh': '3doh_test.npz'
    },
    {   
        'h36m': 'h36m_train.npz',
        'coco': 'coco_2014_train.npz',
        'coco3d': 'coco_2014_train_eft_part.npz',
        'cocoall3d': 'coco_2014_train_eft_all.npz',
        'mpii': 'mpii_train.npz',
        'lsp-orig': 'lsp_dataset_original_train.npz',
        'lspet': 'hr-lspet_train.npz',
        'mpi-inf-3dhp': 'mpi_inf_3dhp_train.npz',
        '3dpw': '3dpw_train.npz',
    }
]

##### CONFIGS #####
hparams = CN()

# General settings
hparams.LOG_DIR = 'logs/experiments'
hparams.METHOD = 'spin' # spin/dsr
hparams.EXP_NAME = 'default'
hparams.EXP_ID = None
hparams.RUN_TEST = False
hparams.SEED_VALUE = -1
hparams.PL_LOGGING = True
hparams.REFRESH_RATE = 1
hparams.FAST_DEV_RUN = False
hparams.DETECT_ANOMALY = False

# Dataset hparams
hparams.DATASET = CN()
hparams.DATASET.NOISE_FACTOR = 0.4
hparams.DATASET.ROT_FACTOR = 30
hparams.DATASET.SCALE_FACTOR = 0.25
hparams.DATASET.BATCH_SIZE = 64
hparams.DATASET.NUM_WORKERS = 8
hparams.DATASET.PIN_MEMORY = True
hparams.DATASET.SHUFFLE_TRAIN = True
hparams.DATASET.SHUFFLE_VAL = True
hparams.DATASET.TRAIN_DS = 'h36m'
hparams.DATASET.VAL_DS = '3dpw'
hparams.DATASET.NUM_IMAGES = -1
hparams.DATASET.IMG_RES = 224
hparams.DATASET.FOCAL_LENGTH = 5000.
hparams.DATASET.MESH_COLOR = 'light_pink'
hparams.DATASET.GENDER_EVAL = True

hparams.DATASET.USE_SYNTHETIC_OCCLUSION = False
hparams.DATASET.OCC_AUG_DATASET = 'pascal'
hparams.DATASET.USE_3D_CONF = False
hparams.DATASET.USE_GENDER = False
hparams.DATASET.USE_HEATMAPS = 'part_segm' # 'hm', 'hm_soft', 'part_segm', 'attention'

# optimizer config
hparams.OPTIMIZER = CN()
hparams.OPTIMIZER.TYPE = 'adam'
hparams.OPTIMIZER.LR = 0.0001
hparams.OPTIMIZER.WD = 0.0
hparams.OPTIMIZER.MM = 0.9

# Training process hparams
hparams.TRAINING = CN()
hparams.TRAINING.RESUME = None
hparams.TRAINING.PRETRAINED = None
hparams.TRAINING.PRETRAINED_LIT = None
hparams.TRAINING.MAX_EPOCHS = 100
hparams.TRAINING.LOG_SAVE_INTERVAL = 40
hparams.TRAINING.LOG_FREQ_TB_IMAGES = 500
hparams.TRAINING.CHECK_VAL_EVERY_N_EPOCH = 1
hparams.TRAINING.RELOAD_DATALOADERS_EVERY_N_EPOCH = 0
hparams.TRAINING.SAVE_IMAGES = False
hparams.TRAINING.USE_AUGM = True
hparams.TRAINING.CAL_ERROR = False
hparams.TRAINING.STRATEGY = None

# Training process hparams
hparams.TESTING = CN()
hparams.TESTING.SAVE_IMAGES = False
hparams.TESTING.SAVE_RESULTS = False
hparams.TESTING.SIDEVIEW = True
hparams.TESTING.LOG_FREQ_TB_IMAGES = 50
hparams.TESTING.DISP_ALL = True


# SSPA method hparams
hparams.SSPA = CN()
hparams.SSPA.BACKBONE = 'resnet50'
hparams.SSPA.REGRESSOR = 'hmr'
hparams.SSPA.CRITERION = 'MSELoss'
hparams.SSPA.COTRAING_LOSS_WEIGHT = 0.
hparams.SSPA.SURFACE_LOSS_WEIGHT = 0.
hparams.SSPA.PSEUDO_LOSS_WEIGHT = 0.
hparams.SSPA.ENERGY_LOSS_WEIGHT = 0.
hparams.SSPA.MESH_LOSS_WEIGHT = 0.
hparams.SSPA.SHAPE_LOSS_WEIGHT = 0.
hparams.SSPA.KEYPOINT_LOSS_WEIGHT = 5.
hparams.SSPA.KEYPOINT_NATIVE_LOSS_WEIGHT = 5.
hparams.SSPA.POSE_LOSS_WEIGHT = 1.
hparams.SSPA.BETA_LOSS_WEIGHT = 0.001
hparams.SSPA.OPENPOSE_TRAIN_WEIGHT = 0.
hparams.SSPA.GT_TRAIN_WEIGHT = 1.
hparams.SSPA.LOSS_WEIGHT = 60.
hparams.SSPA.GAMMA_VAL = 1.0e-1
hparams.SSPA.SIGMA_VAL = 1.0e-7
hparams.SSPA.RENDER_MASK = 6
hparams.SSPA.USE_PRETREATMENT = False
hparams.SSPA.PRETREATMENT_FILTER = []
hparams.SSPA.PRETREATMENT_KERNEL = []
hparams.SSPA.VIT_PATCH = 1
hparams.SSPA.VIT_FILTER = []
hparams.SSPA.USE_POS_EMBED = True
hparams.SSPA.USE_MAE_MASK = False
hparams.SSPA.MAE_MASK_RATIO = 0.
hparams.SSPA.USE_PSEUDO_ATTENTION = False
hparams.SSPA.PSEUDO_METHOD = 'KL-A'
hparams.SSPA.PSEUDO_TEMPRATURE = 1.

# MPQA method hparams
hparams.MPQA = CN()
hparams.MPQA.BACKBONE = 'resnet50'
hparams.MPQA.REGRESSOR = 'hmr'
hparams.MPQA.MESH_LOSS_WEIGHT = 0.
hparams.MPQA.SHAPE_LOSS_WEIGHT = 0.
hparams.MPQA.KEYPOINT_LOSS_WEIGHT = 5.
hparams.MPQA.KEYPOINT_NATIVE_LOSS_WEIGHT = 5.
hparams.MPQA.POSE_LOSS_WEIGHT = 1.
hparams.MPQA.BETA_LOSS_WEIGHT = 0.001
hparams.MPQA.OPENPOSE_TRAIN_WEIGHT = 0.
hparams.MPQA.GT_TRAIN_WEIGHT = 1.
hparams.MPQA.LOSS_WEIGHT = 60.
hparams.MPQA.GAMMA_VAL = 1.0e-1
hparams.MPQA.SIGMA_VAL = 1.0e-7
hparams.MPQA.NUM_CLS = 6
hparams.MPQA.USE_PRETREATMENT = False
hparams.MPQA.PRETREATMENT_FILTER = []
hparams.MPQA.PRETREATMENT_KERNEL = []
hparams.MPQA.VIT_PATCH = 1
hparams.MPQA.VIT_FILTER = []
hparams.MPQA.USE_POS_EMBED = True
hparams.MPQA.USE_MAE_MASK = False
hparams.MPQA.MAE_MASK_RATIO = 0.
hparams.MPQA.USE_PSEUDO_ATTENTION = False
hparams.MPQA.PSEUDO_METHOD = 'KL-A'
hparams.MPQA.PSEUDO_TEMPRATURE = 1.


def get_hparams_defaults():
    """Get a yacs hparamsNode object with default values for my_project."""
    # Return a clone so that the defaults will not be altered
    # This is for the "local variable" use pattern
    return hparams.clone()


def update_hparams(hparams_file):
    hparams = get_hparams_defaults()
    hparams.merge_from_file(hparams_file)
    return hparams.clone()


def update_hparams_from_dict(cfg_dict):
    hparams = get_hparams_defaults()
    cfg = hparams.load_cfg(str(cfg_dict))
    hparams.merge_from_other_cfg(cfg)
    return hparams.clone()


def get_grid_search_configs(config, excluded_keys=[]):
    """
    :param config: dictionary with the configurations
    :return: The different configurations
    """

    def bool_to_string(x: Union[List[bool], bool]) -> Union[List[str], str]:
        """
        boolean to string conversion
        :param x: list or bool to be converted
        :return: string converted thinghat
        """
        if isinstance(x, bool):
            return [str(x)]
        for i, j in enumerate(x):
            x[i] = str(j)
        return x

    # exclude from grid search

    flattened_config_dict = flatten(config, reducer='path')
    hyper_params = []

    for k,v in flattened_config_dict.items():
        if isinstance(v,list):
            if k in excluded_keys:
                flattened_config_dict[k] = ['+'.join(v)]
            elif len(v) > 1:
                hyper_params += [k]

        if isinstance(v, list) and isinstance(v[0], bool) :
            flattened_config_dict[k] = bool_to_string(v)

        if not isinstance(v,list):
            if isinstance(v, bool):
                flattened_config_dict[k] = bool_to_string(v)
            else:
                flattened_config_dict[k] = [v]

    keys, values = zip(*flattened_config_dict.items())
    experiments = [dict(zip(keys, v)) for v in itertools.product(*values)]

    for exp_id, exp in enumerate(experiments):
        for param in excluded_keys:
            exp[param] = exp[param].strip().split('+')
        for param_name, param_value in exp.items():
            # print(param_name,type(param_value))
            if isinstance(param_value, list) and (param_value[0] in ['True', 'False']):
                exp[param_name] = [True if x == 'True' else False for x in param_value]
            if param_value in ['True', 'False']:
                if param_value == 'True':
                    exp[param_name] = True
                else:
                    exp[param_name] = False

        experiments[exp_id] = unflatten(exp, splitter='path')
    return experiments, hyper_params

def run_grid_search_experiments(
        cfg_id,
        cfg_file,
        script='main.py',
):
    cfg = yaml.load(open(cfg_file), Loader=yaml.FullLoader)

    # parse config file to get a list of configs and related hyperparameters
    different_configs, hyperparams = get_grid_search_configs(
        cfg,
        excluded_keys=[],
    )
    logger.info(f'Grid search hparams: \n {hyperparams}')

    different_configs = [update_hparams_from_dict(c) for c in different_configs]
    logger.info(f'======> Number of experiment configurations is {len(different_configs)}')

    config_to_run = CN(different_configs[cfg_id])

    # ==== create logdir using hyperparam settings
    logtime = time.strftime('%d-%m-%Y_%H-%M-%S')
    logdir = f'{logtime}_{config_to_run.EXP_NAME}'

    def get_from_dict(dict, keys):
        return reduce(operator.getitem, keys, dict)

    exp_id = ''
    for hp in hyperparams:
        v = get_from_dict(different_configs[cfg_id], hp.split('/'))
        exp_id += f'{hp.replace("/", ".").replace("_", "").lower()}-{v}'


    config_to_run.EXP_ID = f'{config_to_run.EXP_NAME}'
    if exp_id:
        logdir += f'_{exp_id}'
        config_to_run.EXP_ID += f'/{exp_id}'

    logdir = os.path.join(config_to_run.LOG_DIR, config_to_run.METHOD, config_to_run.EXP_NAME, logdir)
    os.makedirs(logdir, exist_ok=True)
    shutil.copy(src=cfg_file, dst=os.path.join(config_to_run.LOG_DIR, 'config.yaml'))

    config_to_run.LOG_DIR = logdir

    def save_dict_to_yaml(obj, filename, mode='w'):
        with open(filename, mode) as f:
            yaml.dump(obj, f, default_flow_style=False)

    # save config
    save_dict_to_yaml(
        unflatten(flatten(config_to_run)),
        os.path.join(config_to_run.LOG_DIR, 'config_to_run.yaml')
    )

    return config_to_run
