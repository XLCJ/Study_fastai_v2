
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/Callbacks_databunch_Lesson3.ipynb

import torch
from torch import nn, optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
import re
from functools import partial
import math
import matplotlib.pyplot as plt


class myDataset():
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __len__(self):
        return self.x.shape[0]

    def __getitem__(self, i):
        return self.x[i], self.y[i]


def get_dls(ds_train, ds_valid, bs, **kwargs):
    return DataLoader(ds_train, bs, shuffle=True, **kwargs), DataLoader(ds_valid, bs, shuffle=False, **kwargs)


class DataBunch():
    def __init__(self, dl_train, dl_valid, c=None):
        self.dl_train = dl_train
        self.dl_valid = dl_valid
        self.c = c  # number of output classes

    @property  # make an alias for train_ds
    def train_ds(self):
        return self.dl_train.dataset

    @property
    def valid_ds(self):
        return self.dl_valid.dataset


def accuracy(pred, targ):
    return (torch.argmax(pred, dim=1) == targ).float().mean()


# camel case styple to snake case style naming, to be checked later
_camel_re1 = re.compile('(.)([A-Z][a-z]+)')
_camel_re2 = re.compile('([a-z0-9])([A-Z])')


def camel2snake(name):
    s1 = re.sub(_camel_re1, r'\1_\2', name)
    return re.sub(_camel_re2, r'\1_\2', s1).lower()


class Callback():
    _order = 0  # used later to set order of the callback calls

    def set_runner(self, runner):
        self.runner = runner

    def __getattr__(self, key):  # fetch the requested parameter from runner
        return getattr(self.runner, key)  # most hardwork is here

    @property
    def name(self):
        name = re.sub(r'Callback$', '', self.__class__.__name__)
        return camel2snake(name or 'callback')


class TrainEvalCallback(Callback):
    def begin_fit(self):
        self.runner.epochs_elp = 0.  # number of epochs elapsed during training
        self.runner.batch_elp = 0.  # number of batches elapsed
        # default return None

    def begin_epoch(self):
        self.runner.epochs_elp = self.ep  # will be provided in training loop
        self.model.train()  # set by runner property
        self.runner.in_train = True

    def after_batch(self):
        if not self.in_train:
            return
        self.runner.epochs_elp += 1. / self.num_batch  # this will be run num_batch times during training/valid phases
        self.runner.batch_elp += 1

    def begin_validation(self):
        self.model.eval()  # set by runner property
        self.runner.in_train = False


# helper function: standardize everything into lists
from typing import Iterable


def listify(inp):
    if inp is None:
        return []
    if isinstance(inp, list):
        return inp
    if isinstance(inp, Iterable):
        return list(inp)
    return [inp]


class Runner():  # take callbacks and run the training
    def __init__(self, cbs=None, cb_funcs=None):
        # gather all callbacks
        cbs = listify(cbs)
        for cbf in listify(cb_funcs):
            cb = cbf()
            setattr(self, cb.name, cb)  # name done by base callback class
            cbs.append(cb)
        self.cbs = [TrainEvalCallback()] + cbs  # always need the traineval callback
        # set flag
        self.stop = False

    def __call__(self, cb_name):
        # search through all callbacks in given order
        for cb in sorted(self.cbs, key=lambda x: x._order):
            f = getattr(cb, cb_name, None)  # return None if not found
            if f and f():  # if callback name not found, continue the process (by returning false)
                return True  # a normally-exited f() will return False, so if it returns true, process will stop here
        return False  # False == continue running == don't stop

    @property
    def model(self):
        return self.learn.model

    @property
    def opt(self):
        return self.learn.opt

    @property
    def loss_func(self):
        return self.learn.loss_func

    @property
    def data(self):
        return self.learn.data

    def one_batch(self, xb, yb):
        self.xb, self.yb = xb, yb
        if self('begin_batch'):
            return
        self.pred = self.model(xb)
        if self('after_pred'):
            return
        self.loss = self.loss_func(self.pred, yb)
        if self('after_loss') or not self.in_train:
            return
        self.loss.backward()
        if self('after_backward'):
            return
        self.opt.step()
        if self('after_step'):
            return
        self.opt.zero_grad()

    def all_batches(self, dl):
        self.num_batch = len(dl)
        for xb, yb in dl:
            if self.stop:
                break
            self.one_batch(xb, yb)
            self('after_batch')
        self.stop = False

    def fit(self, epochs, learn):
        self.epochs, self.learn = epochs, learn
        try:
            for cb in self.cbs:
                cb.set_runner(self)  # each callback is a sub-class of Callback

            if self('begin_fit'):
                return
            for ep in range(epochs):
                self.ep = ep
                if not self('begin_epoch'):
                    self.all_batches(self.data.dl_train)

                with torch.no_grad():
                    if not self('begin_validation'):
                        self.all_batches(self.data.dl_valid)
                if self('after_epoch'):
                    break
        finally:
            self('after_fit')
            self.learn = None


class AvgStats():
    def __init__(self, metrics, in_train):
        self.metrics = listify(metrics)
        self.in_train = in_train

    def reset(self):
        self.tot_loss = 0.
        self.count = 0
        self.tot_mets = [0.] * len(self.metrics)

    @property
    def all_stats(self):
        return [self.tot_loss.item()] + self.tot_mets

    @property
    def avg_stats(self):
        return [st / self.count for st in self.all_stats]

    @property
    def metric_names(self):
        return ['loss'] + [met.__name__ for met in self.metrics]

    def __repr__(self):  # improve this to print names as well
        if not self.count:
            return ''
        return f"{'train' if self.in_train else 'valid'}: {[(name + ' = ' + str(st)) for name, st in zip(self.metric_names, self.avg_stats)]}"

    def accumulate(self, runner):  # accumulate total metrics cost
        batch_size = runner.xb.shape[0]
        self.tot_loss += runner.loss * batch_size  # crossentropyloss was averaged
        self.count += batch_size

        for i, m in enumerate(self.metrics):
            self.tot_mets[i] += m(runner.pred, runner.yb) * batch_size


class AvgStatsCallback(Callback):
    def __init__(self, metrics):
        self.train_stats = AvgStats(metrics, True)
        self.valid_stats = AvgStats(metrics, False)

    def begin_epoch(self):
        self.train_stats.reset()
        self.valid_stats.reset()

    def after_loss(self):
        stats = self.train_stats if self.in_train else self.valid_stats
        with torch.no_grad():
            stats.accumulate(self.runner)  # get from the Callback class

    def after_epoch(self):
        print(self.train_stats)  # call __repr__
        print(self.valid_stats)


def get_model(data, lr=0.5, nh=50):  # used the databunch from previous section
    fan_in = data.train_ds.x.shape[1]  # this data is databunch
    model = nn.Sequential(nn.Linear(fan_in, nh), nn.ReLU(), nn.Linear(nh, data.c))
    return model, optim.SGD(model.parameters(), lr=lr)


class Learner():
    def __init__(self, model, opt, loss_func, data):
        self.model = model
        self.loss_func = loss_func
        self.opt = opt
        self.data = data


class Recorder(Callback):
    # when _order not defined, will use _order=0 from base class
    def begin_fit(self):
        self.lrs = []
        self.losses = []

    def after_batch(self):
        if not self.in_train:
            return
        self.lrs.append(self.opt.param_groups[-1]['lr'])
        self.losses.append(self.loss.detach().cpu())

    def plot_lr(self):
        plt.plot(self.lrs)

    def plot_loss(self):
        plt.plot(self.losses)


class ParamScheduler(Callback):
    # simply reset desired parameter in param_groups using sched_func
    _order = 1  # start later than TrainEvalCallback etc

    def __init__(self, pname, sched_func):
        self.pname = pname
        self.sched_func = sched_func

    def set_param(self):
        for pg in self.opt.param_groups:
            pg[self.pname] = self.sched_func(self.epochs_elp / self.epochs)  # percent epoch elapsed

    def begin_batch(self):
        if self.in_train:
            self.set_param()


def combine_scheds(pcts, scheds):
    assert sum(pcts) == 1
    pcts = torch.tensor([0] + listify(pcts))
    assert torch.all(pcts >= 0)
    pcts = torch.cumsum(pcts, 0)  # pcts is cumsum now

    def _inner(pos):
        idx = (pos >= pcts).nonzero().max()  # find out which scheds should currently be used
        actual_pos = (pos - pcts[idx]) / (pcts[idx + 1] - pcts[idx])  # percent pos wrt current schedule
        return scheds[idx](actual_pos)
    return _inner
