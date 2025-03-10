import pandas as pd
import logging
import yaml
import torch
from sklearn.model_selection import train_test_split
import inspect
from pathlib import Path
import os
import json
import matplotlib.pyplot as plt

from app.machine_learning.models_pytorch import PytorchModel


def calculate_w_a_difference(dataframe, gases):
    for gas in gases:
        w_column = f"RAW_ADC_{gas}_W"
        a_column = f"RAW_ADC_{gas}_A"
        if w_column in dataframe.columns and a_column in dataframe.columns:
            dataframe[f"{gas}_W_A"] = dataframe[w_column] - dataframe[a_column]
            dataframe.drop([w_column, a_column], inplace=True, axis=1)
        else:
            print(f"Warning: Columns for {gas} not found in the dataframe.")
    return dataframe


def align_dataframes_by_time(df1, df2):
    df1.index = pd.to_datetime(df1.index)
    df2.index = pd.to_datetime(df2.index)

    common_times = df1.index.intersection(df2.index)

    df1_aligned = df1.loc[common_times]
    df2_aligned = df2.loc[common_times]
    return df1_aligned, df2_aligned


def train_test_split_pytorch(inputs, targets, test_size, shuffle):
    inputs_train, inputs_test, targets_train, targets_test = train_test_split(inputs,
                                                                                targets,
                                                                                test_size=test_size,
                                                                                shuffle=shuffle)

    inputs_train_tensor = map_to_tensor(inputs_train)
    inputs_test_tensor = map_to_tensor(inputs_test)
    targets_train_tensor = map_to_tensor(targets_train)
    targets_test_tensor = map_to_tensor(targets_test)

    targets_train_tensor = add_dimension(targets_train_tensor)
    targets_test_tensor = add_dimension(targets_test_tensor)

    return inputs_train_tensor, inputs_test_tensor, targets_train_tensor, targets_test_tensor


def add_dimension(targets_train_tensor):
    targets_train_tensor = targets_train_tensor.unsqueeze(1)
    return targets_train_tensor


def map_to_tensor(inputs_train):
    inputs_train_tensor = torch.tensor(inputs_train.values, dtype=torch.float32)
    return inputs_train_tensor


def create_result_data_from_pytorch(true_values: torch.Tensor, prediction_values: torch.Tensor) -> pd.DataFrame:
    compare_dataframe = pd.DataFrame()
    compare_dataframe["True"] = true_values.detach().numpy().flatten()
    compare_dataframe["Prediction"] = prediction_values.detach().numpy().flatten()
    return compare_dataframe


def create_result_data(true_values, prediction_values) -> pd.DataFrame:
    compare_dataframe = pd.DataFrame()
    compare_dataframe["True"] = true_values
    compare_dataframe["Prediction"] = prediction_values
    return compare_dataframe


def save_parameters_from_pytorch(hyperparameters: dict,
                                 model: PytorchModel,
                                 directory: Path) -> None:
    parameters = hyperparameters
    parameters["training_loss"] = model.training_loss
    parameters["validation_loss"] = model.validation_loss
    with open(directory / Path("parameters.json"), 'w') as convert_file:
        convert_file.write(json.dumps(parameters))


def save_predictions(dataframe: pd.DataFrame, directory: Path) -> None:
    dataframe.to_csv(directory / Path("predictions.csv"))


def save_plot(results, directory: Path):
    plt.plot(results)
    plt.savefig(directory / Path("predictions.png"))


def get_config(file: str) -> dict:
    os_independent_path = _get_caller_directory(2) / Path(file)
    try:
        with open(os_independent_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"No config found in directory")
    except IOError:
        logging.error(f"IOError: An I/O error occurred")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def create_run_directory() -> Path:
    os_independent_path = _get_caller_directory(2)
    results_path = os_independent_path / Path("results")

    if not os.path.exists(results_path):
        os.makedirs(results_path)

    number_of_files = len(os.listdir(results_path))
    run_path = os_independent_path / Path("results" / Path(f"run_{number_of_files + 1}"))
    os.makedirs(run_path)
    return run_path


def _get_caller_directory(stack_position: int) -> Path:
    caller_file = inspect.stack()[stack_position].filename
    return Path(caller_file).parent