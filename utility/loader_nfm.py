import os
import time
import random
import collections

import torch
import numpy as np
import pandas as pd
import scipy.sparse as sp


class DataLoaderNFM(object):

    def __init__(self, args, logging):
        self.args = args
        self.data_name = args.data_name
        self.use_pretrain = args.use_pretrain
        self.pretrain_embedding_dir = args.pretrain_embedding_dir

        self.train_batch_size = args.train_batch_size
        self.test_batch_size = args.test_batch_size

        data_dir = os.path.join(args.data_dir, args.data_name)
        train_file = os.path.join(data_dir, 'train.txt')
        test_file = os.path.join(data_dir, 'test.txt')
        kg_file = os.path.join(data_dir, "kg_final.txt")

        self.cf_train_data, self.train_user_dict = self.load_cf(train_file)
        self.cf_test_data, self.test_user_dict = self.load_cf(test_file)
        self.statistic_cf()

        kg_data = self.load_kg(kg_file)
        self.construct_data(kg_data)
        self.print_info(logging)

        if self.use_pretrain == 1:
            self.load_pretrained_data()

    def load_cf(self, filename):
        user = []
        item = []
        user_dict = dict()

        lines = open(filename, 'r').readlines()
        for l in lines:
            tmp = l.strip()
            inter = [int(i) for i in tmp.split()]

            if len(inter) > 1:
                user_id, item_ids = inter[0], inter[1:]
                item_ids = list(set(item_ids))

                # 这里user和item提取出关系放在list中保持对应关系
                # user_dict作为字典重新保持关系
                for item_id in item_ids:
                    user.append(user_id)
                    item.append(item_id)
                user_dict[user_id] = item_ids

        user = np.array(user, dtype=np.int32)
        item = np.array(item, dtype=np.int32)
        return (user, item), user_dict

    def statistic_cf(self):
        self.n_users = max(max(self.cf_train_data[0]), max(self.cf_test_data[0])) + 1
        self.n_items = max(max(self.cf_train_data[1]), max(self.cf_test_data[1])) + 1
        self.n_cf_train = len(self.cf_train_data[0])
        self.n_cf_test = len(self.cf_test_data[0])

    def load_kg(self, filename):
        kg_data = pd.read_csv(filename, sep=' ', names=['h', 'r', 't'], engine='python')
        kg_data = kg_data.drop_duplicates()  # 去除重复项
        # print(kg_data)  # [10896 rows x 3 columns]
        return kg_data

    def construct_data(self, kg_data):
        # re-map user id
        self.n_entities = max(max(kg_data['h']), max(kg_data['t'])) + 1
        self.n_users_entities = self.n_users + self.n_entities

        self.cf_train_data = (np.array(list(map(lambda d: d + self.n_entities, self.cf_train_data[0]))).astype(np.int32), self.cf_train_data[1].astype(np.int32))
        self.cf_test_data = (np.array(list(map(lambda d: d + self.n_entities, self.cf_test_data[0]))).astype(np.int32), self.cf_test_data[1].astype(np.int32))

        # 把dict中的list转换为数组，np.unique()去重排序
        self.train_user_dict = {k + self.n_entities: np.unique(v).astype(np.int32) for k, v in self.train_user_dict.items()}
        self.test_user_dict = {k + self.n_entities: np.unique(v).astype(np.int32) for k, v in self.test_user_dict.items()}

        # construct feature matrix
        feat_rows = list(range(self.n_items))
        feat_cols = list(range(self.n_items))
        feat_data = [1] * self.n_items

        filtered_kg_data = kg_data[kg_data['h'] < self.n_items]
        feat_rows += filtered_kg_data['h'].tolist()
        feat_cols += filtered_kg_data['t'].tolist()
        feat_data += [1] * filtered_kg_data.shape[0]

        # 24915
        # (465191, 3)
        # 490106
        # 490106
        # 24915 113487

        # print(self.n_items)
        # print(filtered_kg_data.shape)
        # print(len(feat_rows))
        # print(len(feat_cols))
        # print(self.n_items, self.n_entities)

        # 250
        # (10896, 3)
        # 11146
        # 11146
        # 250 207

        # scipy.sparse:创建稀疏矩阵  tocsr():返回稀疏矩阵的csr_matrix形式
        # 稀疏格式的单位矩阵
        self.user_matrix = sp.identity(self.n_users).tocsr()
        # COO不支持元素的存取和增删
        self.feat_matrix = sp.coo_matrix((feat_data, (feat_rows, feat_cols)), shape=(self.n_items, self.n_entities)).tocsr()

    def print_info(self, logging):
        logging.info('n_users:              %d' % self.n_users)
        logging.info('n_items:              %d' % self.n_items)
        logging.info('n_entities:           %d' % self.n_entities)
        logging.info('n_users_entities:     %d' % self.n_users_entities)

        logging.info('n_cf_train:           %d' % self.n_cf_train)
        logging.info('n_cf_test:            %d' % self.n_cf_test)

        logging.info('shape of user_matrix: {}'.format(self.user_matrix.shape))
        logging.info('shape of feat_matrix: {}'.format(self.feat_matrix.shape))

    def sample_pos_items_for_u(self, user_dict, user_id, n_sample_pos_items):
        pos_items = user_dict[user_id]
        n_pos_items = len(pos_items)

        sample_pos_items = []
        while True:
            if len(sample_pos_items) == n_sample_pos_items:
                break

            pos_item_idx = np.random.randint(low=0, high=n_pos_items, size=1)[0]
            pos_item_id = pos_items[pos_item_idx]
            if pos_item_id not in sample_pos_items:
                sample_pos_items.append(pos_item_id)
        return sample_pos_items

    def sample_neg_items_for_u(self, user_dict, user_id, n_sample_neg_items):
        pos_items = user_dict[user_id]

        sample_neg_items = []
        while True:
            if len(sample_neg_items) == n_sample_neg_items:
                break

            neg_item_id = np.random.randint(low=0, high=self.n_items, size=1)[0]
            if neg_item_id not in pos_items and neg_item_id not in sample_neg_items:
                sample_neg_items.append(neg_item_id)
        return sample_neg_items

    def convert_coo2tensor(self, coo):
        values = coo.data
        indices = np.vstack((coo.row, coo.col))

        i = torch.LongTensor(indices)
        v = torch.FloatTensor(values)
        shape = coo.shape

        return torch.sparse.FloatTensor(i, v, torch.Size(shape))

    def generate_train_batch(self, user_dict):
        exist_users = user_dict.keys()
        if self.train_batch_size <= len(exist_users):
            batch_user = random.sample(exist_users, self.train_batch_size)
        else:
            batch_user = [random.choice(exist_users) for _ in range(self.train_batch_size)]

        batch_pos_item, batch_neg_item = [], []
        for u in batch_user:
            batch_pos_item += self.sample_pos_items_for_u(user_dict, u, 1)
            batch_neg_item += self.sample_neg_items_for_u(user_dict, u, 1)

        batch_user_sp = self.user_matrix[[i - self.n_entities for i in batch_user]]
        batch_pos_item_sp = self.feat_matrix[batch_pos_item]
        batch_neg_item_sp = self.feat_matrix[batch_neg_item]

        pos_feature_values = sp.hstack([batch_pos_item_sp, batch_user_sp])
        neg_feature_values = sp.hstack([batch_neg_item_sp, batch_user_sp])

        pos_feature_values = self.convert_coo2tensor(pos_feature_values.tocoo())
        neg_feature_values = self.convert_coo2tensor(neg_feature_values.tocoo())

        return pos_feature_values, neg_feature_values

    def generate_test_batch(self, batch_user, batch_item):
        batch_user_sp = self.user_matrix[np.array(batch_user) - self.n_entities]
        batch_item_sp = self.feat_matrix[batch_item]
        feature_values = sp.hstack([batch_item_sp, batch_user_sp])
        feature_values = self.convert_coo2tensor(feature_values.tocoo())
        return feature_values

    def load_pretrained_data(self):
        pre_model = 'mf'
        pretrain_path = '%s/%s/%s.npz' % (self.pretrain_embedding_dir, self.data_name, pre_model)
        pretrain_data = np.load(pretrain_path)
        self.user_pre_embed = pretrain_data['user_embed']
        self.item_pre_embed = pretrain_data['item_embed']

        assert self.user_pre_embed.shape[0] == self.n_users
        assert self.item_pre_embed.shape[0] == self.n_items
        assert self.user_pre_embed.shape[1] == self.args.embed_dim
        assert self.item_pre_embed.shape[1] == self.args.embed_dim



