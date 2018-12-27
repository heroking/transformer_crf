#!/usr/bin python3
# -*- coding: utf-8 -*-
# @Time    : 18-12-27 上午9:46
# @Author  : 林利芳
# @File    : run.py
from config.config import *
from model.model import Model
from utils.metric import get_ner_fmeasure, recover_label
from utils.utils import create_vocab, load_data, generate_data, batch_data
from config.hyperparams import HyperParams as hp
import tensorflow as tf
import numpy as np


def train(is_vocab=False):
	if is_vocab:
		create_vocab()
	word2id, id2word = load_data(TOKEN_DATA)
	tag2id, id2tag = load_data(TAG_DATA)
	x_train, y_train, seq_lens, _, _ = generate_data(TRAIN_DATA, word2id, tag2id, max_len=hp.max_len)
	x_dev, y_dev, dev_seq_lens, _, _ = generate_data(DEV_DATA, word2id, tag2id, max_len=hp.max_len)
	vocab_size = len(word2id)
	num_tags = len(tag2id)
	model = Model(vocab_size, num_tags, is_training=True)
	sv = tf.train.Supervisor(graph=model.graph, save_model_secs=0)
	with sv.managed_session() as sess:
		for epoch in range(1, hp.num_epochs + 1):
			if sv.should_stop():
				break
			train_loss = []
			for x_batch, y_batch, len_batch in batch_data(x_train, y_train, seq_lens, hp.batch_size):
				feed_dict = {model.x: x_batch, model.y: y_batch, model.seq_lens: len_batch}
				loss, _ = sess.run([model.loss, model.train_op], feed_dict=feed_dict)
				train_loss.append(loss)
			
			dev_loss = []
			golden_lists, predict_lists = [], []
			for x_batch, y_batch, len_batch in batch_data(x_dev, y_dev, dev_seq_lens, hp.batch_size):
				feed_dict = {model.x: x_batch, model.y: y_batch, model.seq_lens: len_batch}
				loss, logits = sess.run([model.loss, model.logits], feed_dict)
				dev_loss.append(loss)
				
				transition = model.transition.eval(session=sess)
				pre_seq = model.predict(logits, transition, len_batch)
				pre_label, gold_label = recover_label(pre_seq, y_batch, len_batch, id2tag)
				predict_lists.extend(pre_label)
				golden_lists.extend(gold_label)
			acc, p, r, f = get_ner_fmeasure(golden_lists, predict_lists)
			print('epoch:\t{}\ttrain loss:\t{}\tdev loss:\t{}\n'.format(epoch, np.round(np.mean(train_loss), 4),
																		np.round(np.mean(dev_loss), 4)))
			print('accuracy:\t{}\tp:\t{}\tr:\t{}\tf:\t{}\n'.format(acc, p, r, f))
			# gs = sess.run(model.global_step)
			# sv.saver.save(sess, logdir + '/model_epoch_{}_{}'.format(epoch, gs))


def dev():
	word2id, id2word = load_data(TOKEN_DATA)
	tag2id, id2tag = load_data(TAG_DATA)
	x_dev, y_dev, dev_seq_lens, _, _ = generate_data(DEV_DATA, word2id, tag2id, max_len=hp.max_len)
	vocab_size = len(word2id)
	num_tags = len(tag2id)
	model = Model(vocab_size, num_tags, is_training=False)
	
	with model.graph.as_default():
		sv = tf.train.Supervisor()
		with sv.managed_session() as sess:
			sv.saver.restore(sess, tf.train.latest_checkpoint(logdir))
			golden_lists, predict_lists = [], []
			for x_batch, y_batch, len_batch in batch_data(x_dev, y_dev, dev_seq_lens, hp.batch_size):
				feed_dict = {model.x: x_batch, model.seq_lens: len_batch}
				logits = sess.run(model.logits, feed_dict)
				transition = model.transition.eval(session=sess)
				pre_seq = model.predict(logits, transition)
				pre_label, gold_label = recover_label(pre_seq, y_batch, len_batch, id2tag)
				predict_lists.extend(pre_label)
				golden_lists.extend(gold_label)
			acc, p, r, f = get_ner_fmeasure(golden_lists, predict_lists)
			print('accuracy:\t{}\tp:\t{}\tr:\t{}\tf:\t{}\n'.format(acc, p, r, f))


if __name__ == "__main__":
	train(is_vocab=True)
	# dev()