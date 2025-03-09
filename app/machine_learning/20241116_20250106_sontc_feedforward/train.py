import json
import os
from pathlib import Path

from app.database.Influx_db_connector import InfluxDBConnector
from app.database.influx_buckets import InfluxBuckets
from app.database.influx_query_builder import InfluxQueryBuilder
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset
from app.machine_learning.PytorchModels import FeedForwardModel, PytorchModel
from app.utils import calculate_w_a_difference, get_config, align_dataframes_by_time, create_run_directory
import matplotlib.pyplot as plt

if __name__ == "__main__":
    connection = InfluxDBConnector()

    # TODO: Feuchte und Temperatur hinzufügen
    inputs_query = InfluxQueryBuilder() \
        .set_bucket(InfluxBuckets.AQSN_MINUTE_CALIBRATION_BUCKET.value) \
        .set_range("2024-11-16T00:00:00Z", "2025-01-06T23:00:00Z") \
        .set_measurement("sont_c") \
        .set_fields(["RAW_ADC_NO2_W",
                     "RAW_ADC_NO2_A",
                     "RAW_ADC_NO_W",
                     "RAW_ADC_NO_A",
                     "RAW_ADC_O3_W",
                     "RAW_ADC_O3_A",
                     ]) \
        .build()
    input_data = connection.query_dataframe(inputs_query)

    target_query = InfluxQueryBuilder() \
        .set_bucket(InfluxBuckets.LUBW_MINUTE_BUCKET.value) \
        .set_range("2024-11-16T00:00:00Z", "2025-01-06T23:00:00Z") \
        .set_measurement("DEBW015") \
        .set_fields(["NO2"]) \
        .build()
    target_data = connection.query_dataframe(target_query)

    align_inputs, align_targets = align_dataframes_by_time(input_data, target_data)
    gases = ["NO2", "NO", "O3"]
    align_input_differences = calculate_w_a_difference(align_inputs, gases)

    #TODO: Normalisierung der Daten

    inputs_train, inputs_test, targets_train, targets_test = train_test_split(align_input_differences,
                                                        align_targets["NO2"],
                                                        test_size=0.2,
                                                        shuffle=False)

    inputs_train_tensor = torch.tensor(inputs_train.values, dtype=torch.float32)
    inputs_test_tensor = torch.tensor(inputs_test.values, dtype=torch.float32)
    targets_train_tensor = torch.tensor(targets_train.values, dtype=torch.float32)
    targets_test_tensor = torch.tensor(targets_test.values, dtype=torch.float32)

    targets_train_tensor = targets_train_tensor.unsqueeze(1)
    targets_test_tensor = targets_test_tensor.unsqueeze(1)

    hyperparameters = get_config("workflow_config.yaml")

    train_loader = DataLoader(dataset=TensorDataset(inputs_train_tensor, targets_train_tensor),
                              batch_size=hyperparameters["batch_size"], shuffle=True)
    test_loader = DataLoader(dataset=TensorDataset(inputs_test_tensor, targets_test_tensor),
                             batch_size=hyperparameters["batch_size"], shuffle=True)

    model: PytorchModel = FeedForwardModel(3, hyperparameters["learning_rate"])

    for epoch in range(hyperparameters["epochs"]):
        model.backward(train_loader, epoch, hyperparameters["epochs"])
        model.validate(test_loader)

    prediction = model.forward(inputs_test_tensor)

    run_directory = create_run_directory()

    parameters = hyperparameters
    parameters["training_loss"] = model.training_loss
    parameters["validation_loss"] = model.validation_loss
    with open(run_directory / Path("parameters.json"), 'w') as convert_file:
        convert_file.write(json.dumps(parameters))

    compare_dataframe = pd.DataFrame()
    compare_dataframe["True"] = targets_test
    compare_dataframe["Prediction"] = prediction.detach().numpy()
    compare_dataframe.to_csv(run_directory / Path("predictions.csv"))

    plt.plot(compare_dataframe)
    plt.savefig(run_directory / Path("predictions.png"))



