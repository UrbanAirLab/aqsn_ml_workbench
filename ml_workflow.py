from sklearn.model_selection import train_test_split
import keras
import matplotlib.pyplot as plt
from utils import SensorData


def workflow(model, data: SensorData) -> None:
    future_sontc_data = SensorData(file_path_lubw="./data/DEBW015_20241211-202241228.csv",
                                   file_path_aqsn="./data/sont_c_20241211-202241228.csv",
                                   in_hour=True)

    x_train, x_test, y_train, y_test = train_test_split(data.get_difference_electrodes_no2,
                                                        data.get_NO2,
                                                        test_size=0.2,
                                                        shuffle=False)


    model.compile(optimizer=keras.optimizers.Adam(0.001) ,loss="mean_squared_error")
    model.fit(x_train, y_train, epochs=5, batch_size=3)

    predictions = model.predict(x_test)
    deviation = y_test - predictions.flatten()
    further_prediction = model.predict(future_sontc_data.get_difference_electrodes_no2)

    fig, axes = plt.subplots(2, 2)
    axes = axes.flatten()
    axes[0].plot(y_test, label="y_test")
    axes[1].plot(predictions, label="predictions")
    axes[2].plot(deviation, label="y_test - predicition")
    axes[3].plot(further_prediction, label="11. dezember ff sont_c")
    axes[3].plot(future_sontc_data.get_NO2, label="11. dezember ff LUBW")
    for ax in axes:
        ax.grid(True)
        ax.legend()
    plt.savefig('./results/results_sontc.png')
    plt.show()
