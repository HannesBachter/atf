#!/usr/bin/env python
import copy
import math
import rospy

from atf_msgs.msg import MetricResult, KeyValue, DataStamped
from atf_metrics import metrics_helper

class CalculateTimeParamHandler:
    def __init__(self):
        """
        Class for returning the corresponding metric class with the given parameter.
        """
        pass

    def parse_parameter(self, testblock_name, params):
        """
        Method that returns the metric method with the given parameter.
        :param params: Parameter
        """
        metrics = []

        # special case for time (can have empty list of parameters, thus adding dummy groundtruth information)
        if params == []:
            params.append({"groundtruth":None, "groundtruth_epsilon":None})

        if type(params) is not list:
            rospy.logerr("metric config not a list")
            return False

        for metric in params:
            # check for optional parameters
            try:
                groundtruth = metric["groundtruth"]
                groundtruth_epsilon = metric["groundtruth_epsilon"]
            except (TypeError, KeyError):
                groundtruth = None
                groundtruth_epsilon = None
            metrics.append(CalculateTime(groundtruth, groundtruth_epsilon))
        return metrics

class CalculateTime:
    def __init__(self, groundtruth, groundtruth_epsilon):
        """
        Class for calculating the time between the trigger 'ACTIVATE' and 'FINISH' on the topic assigned to the
        testblock.
        """
        self.name = 'time'
        self.started = False
        self.finished = False
        self.active = False
        self.groundtruth = groundtruth
        self.groundtruth_epsilon = groundtruth_epsilon
        self.series_mode = None # Time metrics cannot have a series
        self.series = []
        self.data = DataStamped()
        self.start_time = None

    def start(self, status):
        self.start_time = status.stamp
        self.active = True
        self.started = True

    def stop(self, status):
        self.data.stamp = status.stamp
        self.data.data = round((self.data.stamp - self.start_time).to_sec(), 6)
        self.series.append(copy.deepcopy(self.data))  # FIXME handle fixed rates
        self.active = False
        self.finished = True

    def pause(self, status):
        # TODO: Implement pause time calculation
        pass

    def purge(self, status):
        # TODO: Implement purge as soon as pause is implemented
        pass

    def update(self, topic, msg, t):
        pass

    def get_topics(self):
        return []

    def get_result(self):
        metric_result = MetricResult()
        metric_result.name = self.name
        metric_result.started = self.started # FIXME remove
        metric_result.finished = self.finished # FIXME remove
        metric_result.series = []
        metric_result.data = None
        metric_result.groundtruth = self.groundtruth
        metric_result.groundtruth_epsilon = self.groundtruth_epsilon
        
        # assign default value
        metric_result.groundtruth_result = None
        metric_result.groundtruth_error_message = None

        if metric_result.started and metric_result.finished: #  we check if the testblock was ever started and stopped
            # calculate metric data
            if self.series_mode != None:
                metric_result.series = self.series
            metric_result.data = self.series[-1] # take last element from self.series
            metric_result.min = metrics_helper.get_min(self.series)
            metric_result.max = metrics_helper.get_max(self.series)
            metric_result.mean = metrics_helper.get_mean(self.series)
            metric_result.std = metrics_helper.get_std(self.series)

            # fill details as KeyValue messages
            details = []
            metric_result.details = details

            # evaluate metric data
            if metric_result.data != None and metric_result.groundtruth != None and metric_result.groundtruth_epsilon != None:
                if math.fabs(metric_result.groundtruth - metric_result.data.data) <= metric_result.groundtruth_epsilon:
                    metric_result.groundtruth_result = True
                    metric_result.groundtruth_error_message = "all OK"
                else:
                    metric_result.groundtruth_result = False
                    metric_result.groundtruth_error_message = "groundtruth missmatch: %f not within %f+-%f"%(metric_result.data.data, metric_result.groundtruth, metric_result.groundtruth_epsilon)

        if metric_result.data == None:
            metric_result.groundtruth_result = False
            metric_result.groundtruth_error_message = "no result"

        return metric_result
