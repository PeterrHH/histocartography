import numpy as np
import h5py
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, f1_score
from sklearn.metrics import classification_report, confusion_matrix


class LearnedFusion:
    def __init__(self, config):
        self.model_save_path = config.model_save_path
        self.eval_mode = ['train', 'val', 'test']
        self.tumor_types = config.tumor_types
        self.tumor_labels = config.tumor_labels
        self.num_classes = config.num_classes

    def get_troi_ids(self, config, mode, tumor_type):
        trois = []
        filename = config.base_data_split_path + mode + '_list_' + tumor_type + '.txt'
        with open(filename, 'r') as f:
            for line in f:
                line = line.split('\n')[0]
                if line != '':
                    trois.append(line)
        return trois

    def read_data(self, config, mode):
        data_all = np.array([])
        label_all = np.array([])

        for t in range(len(self.tumor_types)):
            data = np.array([])
            label = np.array([])

            troi_ids = self.get_troi_ids(config, mode, self.tumor_types[t])

            with h5py.File(self.model_save_path + mode + '_' + self.tumor_types[t] + '.h5', 'r') as f:
                patch_count = np.array(f['patch_count']).astype(int)
                patch_probabilities = np.array(f['patch_probabilities'])

            start = 0
            for i in range(len(troi_ids)):
                prob = patch_probabilities[start: start + patch_count[i], :]
                start += patch_count[i]

                prob = np.mean(prob, axis=0)
                prob = np.reshape(prob, newshape=(1, -1))

                if i == 0:
                    data = prob
                else:
                    data = np.vstack((data, prob))
                label = np.append(label, self.tumor_labels[t])

            if t == 0:
                data_all = data
                label_all = label
            else:
                data_all = np.vstack((data_all, data))
                label_all = np.concatenate((label_all, label))

        return data_all, label_all

    def compute_statistics(self, true_labels, pred_labels):
        acc = accuracy_score(true_labels, pred_labels)
        f1 = f1_score(true_labels, pred_labels, average='weighted')

        target_names = list(np.arange(self.num_classes))
        target_names = [str(x) for x in target_names]
        cls_report = classification_report(
            true_labels, pred_labels, target_names=target_names)
        conf_matrix = confusion_matrix(true_labels, pred_labels)

        print('classification report:', cls_report)
        print('accuracy:', round(acc, 4))
        print('weighted F1:', round(f1, 4), '\n')
        print(conf_matrix)
        print('\n')

    def evaluate(self):
        pred_train = self.clf.predict(self.train_data)
        pred_val = self.clf.predict(self.val_data)
        pred_test = self.clf.predict(self.test_data)

        train_f1 = f1_score(self.train_labels, pred_train, average='weighted')
        val_f1 = f1_score(self.val_labels, pred_val, average='weighted')
        test_f1 = f1_score(self.test_labels, pred_test, average='weighted')
        return train_f1, val_f1, test_f1

    def cross_C_evaluate(self):
        C = [1, 10, 100, 1000]
        f1_train = np.array([])
        f1_val = np.array([])
        f1_test = np.array([])

        for c in C:
            self.clf = SVC(C=c, kernel='rbf', gamma='auto')
            self.clf.fit(self.train_data, self.train_labels)
            train_f1, val_f1, test_f1 = self.evaluate()
            f1_train = np.append(f1_train, train_f1)
            f1_val = np.append(f1_val, val_f1)
            f1_test = np.append(f1_test, test_f1)

        idx = np.argmax(f1_val)
        print('Best C=', C[idx],
              ' F1: train=', round(f1_train[idx], 4),
              ', val=', round(f1_val[idx], 4),
              ', test=', round(f1_test[idx], 4))

        self.clf = SVC(C=C[idx], kernel='rbf', gamma='auto')
        self.clf.fit(self.train_data, self.train_labels)
        pred_test = self.clf.predict(self.test_data)

        print('STATISTICS for TEST *************************************************************************')
        self.compute_statistics(self.test_labels, pred_test)

    def process(self, config):
        self.train_data, self.train_labels = self.read_data(
            config, mode='train')
        self.val_data, self.val_labels = self.read_data(config, mode='val')
        self.test_data, self.test_labels = self.read_data(config, mode='test')

        self.cross_C_evaluate()