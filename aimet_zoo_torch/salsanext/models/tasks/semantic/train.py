#!/usr/bin/env python3
# pylint: skip-file

# The MIT License
#
# Copyright (c) 2019 Tiago Cortinhal (Halmstad University, Sweden), George Tzelepis (Volvo Technology AB, Volvo Group Trucks Technology, Sweden) and Eren Erdal Aksoy (Halmstad University and Volvo Technology AB, Sweden)
#
# Copyright (c) 2019 Andres Milioto, Jens Behley, Cyrill Stachniss, Photogrammetry and Robotics Lab, University of Bonn.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.



import argparse
import datetime
import os
import shutil
from shutil import copyfile
import __init__ as booger
import yaml
from tasks.semantic.modules.trainer import *
from pip._vendor.distlib.compat import raw_input

from tasks.semantic.modules.SalsaNextAdf import *
from tasks.semantic.modules.SalsaNext import *
#from tasks.semantic.modules.save_dataset_projected import *
import math
from decimal import Decimal

def remove_exponent(d):
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()

def millify(n, precision=0, drop_nulls=True, prefixes=[]):
    millnames = ['', 'k', 'M', 'B', 'T', 'P', 'E', 'Z', 'Y']
    if prefixes:
        millnames = ['']
        millnames.extend(prefixes)
    n = float(n)
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))
    result = '{:.{precision}f}'.format(n / 10**(3 * millidx), precision=precision)
    if drop_nulls:
        result = remove_exponent(Decimal(result))
    return '{0}{dx}'.format(result, dx=millnames[millidx])


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean expected')

if __name__ == '__main__':
    parser = argparse.ArgumentParser("./train.py")
    parser.add_argument(
        '--dataset', '-d',
        type=str,
        required=True,
        help='Dataset to train with. No Default',
    )
    parser.add_argument(
        '--arch_cfg', '-ac',
        type=str,
        required=True,
        help='Architecture yaml cfg file. See /config/arch for sample. No default!',
    )
    parser.add_argument(
        '--data_cfg', '-dc',
        type=str,
        required=False,
        default='config/labels/semantic-kitti.yaml',
        help='Classification yaml cfg file. See /config/labels for sample. No default!',
    )
    parser.add_argument(
        '--log', '-l',
        type=str,
        default="~/output",
        help='Directory to put the log data. Default: ~/logs/date+time'
    )
    parser.add_argument(
        '--name', '-n',
        type=str,
        default="",
        help='If you want to give an aditional discriptive name'
    )
    parser.add_argument(
        '--pretrained', '-p',
        type=str,
        required=False,
        default=None,
        help='Directory to get the pretrained model. If not passed, do from scratch!'
    )
    parser.add_argument(
        '--uncertainty', '-u',
        type=str2bool, nargs='?',
        const=True, default=False,
        help='Set this if you want to use the Uncertainty Version'
    )

    FLAGS, unparsed = parser.parse_known_args()
    FLAGS.log = FLAGS.log + '/logs/' + datetime.datetime.now().strftime("%Y-%-m-%d-%H:%M") + FLAGS.name
    if FLAGS.uncertainty:
        params = SalsaNextUncertainty(20)
        pytorch_total_params = sum(p.numel() for p in params.parameters() if p.requires_grad)
    else:
        params = SalsaNext(20)
        pytorch_total_params = sum(p.numel() for p in params.parameters() if p.requires_grad)
    # print summary of what we will do
    print("----------")
    print("INTERFACE:")
    print("dataset", FLAGS.dataset)
    print("arch_cfg", FLAGS.arch_cfg)
    print("data_cfg", FLAGS.data_cfg)
    print("uncertainty", FLAGS.uncertainty)
    print("Total of Trainable Parameters: {}".format(millify(pytorch_total_params,2)))
    print("log", FLAGS.log)
    print("pretrained", FLAGS.pretrained)
    print("----------\n")
    # print("Commit hash (training version): ", str(
    #    subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()))
    print("----------\n")

    # open arch config file
    try:
        print("Opening arch config file %s" % FLAGS.arch_cfg)
        ARCH = yaml.safe_load(open(FLAGS.arch_cfg, 'r'))
    except Exception as e:
        print(e)
        print("Error opening arch yaml file.")
        quit()

    # open data config file
    try:
        print("Opening data config file %s" % FLAGS.data_cfg)
        DATA = yaml.safe_load(open(FLAGS.data_cfg, 'r'))
    except Exception as e:
        print(e)
        print("Error opening data yaml file.")
        quit()

    # create log folder
    try:
        if FLAGS.pretrained == "":
            FLAGS.pretrained = None
            if os.path.isdir(FLAGS.log):
                if os.listdir(FLAGS.log):
                    answer = raw_input("Log Directory is not empty. Do you want to proceed? [y/n]  ")
                    if answer == 'n':
                        quit()
                    else:
                        shutil.rmtree(FLAGS.log)
            os.makedirs(FLAGS.log)
        else:
            FLAGS.log = FLAGS.pretrained
            print("Not creating new log file. Using pretrained directory")
    except Exception as e:
        print(e)
        print("Error creating log directory. Check permissions!")
        quit()

    # does model folder exist?
    if FLAGS.pretrained is not None:
        if os.path.isdir(FLAGS.pretrained):
            print("model folder exists! Using model from %s" % (FLAGS.pretrained))
        else:
            print("model folder doesnt exist! Start with random weights...")
    else:
        print("No pretrained directory found.")

    # copy all files to log folder (to remember what we did, and make inference
    # easier). Also, standardize name to be able to open it later
    try:
        print("Copying files to %s for further reference." % FLAGS.log)
        copyfile(FLAGS.arch_cfg, FLAGS.log + "/arch_cfg.yaml")
        copyfile(FLAGS.data_cfg, FLAGS.log + "/data_cfg.yaml")
    except Exception as e:
        print(e)
        print("Error copying files, check permissions. Exiting...")
        quit()

    # create trainer and start the training
    trainer = Trainer(ARCH, DATA, FLAGS.dataset, FLAGS.log, FLAGS.pretrained,FLAGS.uncertainty)
    trainer.train()
