#!/usr/bin/env python
import tf
import math
import rospy
import tf2_msgs
import tf2_ros
import threading

class CalculatePathLengthParamHandler:
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
        if type(params) is not list:
            rospy.logerr("metric config not a list")
            return False

        for metric in params:
            # check for optional parameters
            try:
                groundtruth = metric["groundtruth"]
                groundtruth_epsilon = metric["groundtruth_epsilon"]
            except (TypeError, KeyError):
                #rospy.logwarn_throttle(10, "No groundtruth parameters given, skipping groundtruth evaluation for metric 'path_length' in testblock '%s'"%testblock_name)
                groundtruth = None
                groundtruth_epsilon = None
            metrics.append(CalculatePathLength(metric["topic"], metric["root_frame"], metric["measured_frame"], groundtruth, groundtruth_epsilon))
        return metrics

class CalculatePathLength:
    def __init__(self, topic, root_frame, measured_frame, groundtruth, groundtruth_epsilon):
        """
        Class for calculating the distance covered by the given frame in relation to a given root frame.
        The tf data is sent over the tf topic given in the robot_config.yaml.
        :param root_frame: name of the first frame
        :type  root_frame: string
        :param measured_frame: name of the second frame. The distance will be measured in relation to the root_frame.
        :type  measured_frame: string
        """
        self.started = False
        self.finished = False
        self.active = False
        self.groundtruth = groundtruth
        self.groundtruth_epsilon = groundtruth_epsilon
        self.topic = topic
        self.root_frame = root_frame
        self.measured_frame = measured_frame
        self.path_length = 0.0
        self.tf_sampling_freq = 20.0  # Hz
        self.first_value = True
        self.trans_old = []
        self.rot_old = []

        self.t = tf.Transformer(True, rospy.Duration(10.0))

    def start(self, timestamp):
        self.active = True
        self.started = True

    def stop(self, timestamp):
        self.active = False
        self.finished = True

    def pause(self, timestamp):
        self.active = False
        self.first_value = True

    def purge(self, timestamp):
        pass

    def update(self, topic, msg, t):
        #print "update"
        if self.active:
            #print "active"
            #print "topic=", topic, "self.topic=", self.topic
            if topic == self.topic:
                for transform in msg.transforms:
                    #update transformer
                    self.t.setTransform(transform)

                    # get latest transform
                    try:
                        (trans, rot) = self.t.lookupTransform(self.root_frame, self.measured_frame, rospy.Time(0))
                    except tf2_ros.LookupException as e:
                        rospy.logwarn("Exception in metric 'path_length' %s %s",type(e), e)
                        continue

                    if self.first_value:
                        self.trans_old = trans
                        self.rot_old = rot
                        self.first_value = False
                        return
                    #print "transformations: \n", "trans[0]", trans[0], "self.trans_old[0]",self.trans_old[0], "trans[1]", trans[1], "self.trans_old[1]",self.trans_old[1], "trans[2]",trans[2], "self.trans_old[2]",self.trans_old[2], "\n ------------------------------------------------ "
                    path_increment = math.sqrt((trans[0] - self.trans_old[0]) ** 2 + (trans[1] - self.trans_old[1]) ** 2 +
                                            (trans[2] - self.trans_old[2]) ** 2)
                    if(path_increment < 1):
                        #rospy.logwarn("Transformation: %s, Path Increment: %s",str(trans), str(path_increment))
                        self.path_length += path_increment

                    else:
                        rospy.logwarn("Transformation Failed! \n Transformation: %s, Path Increment: %s",str(trans), str(path_increment))

                    self.trans_old = trans
                    self.rot_old = rot

    def get_topics(self):
            return []

    def get_result(self):
        groundtruth_result = None
        details = {"root_frame": self.root_frame, "measured_frame": self.measured_frame}
        if self.started and self.finished: #  we check if the testblock was ever started and stoped
            data = round(self.path_length, 3)
            if self.groundtruth != None and self.groundtruth_epsilon != None:
                if math.fabs(self.groundtruth - data) <= self.groundtruth_epsilon:
                    groundtruth_result = True
                else:
                    groundtruth_result = False
            return "path_length", data, groundtruth_result, self.groundtruth, self.groundtruth_epsilon, details
        else:
            return False