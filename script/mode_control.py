#!/usr/bin/env python
#-*- coding: utf-8 -*-

#-------------------import section-------------------
import copy 
import math         
import rospy
from std_msgs.msg import Int64                                              # 로봇의 모드 메세지 형식
from turson.msg  import Box_data                                            # 박스 데이터 커스텀 메시지
from nav_msgs.msg import Odometry                                           # 로봇의 현재위치 수신
from move_base_msgs.msg import MoveBaseActionResult                         # 로봇의 Navigation goal 도착여부 수신
from geometry_msgs.msg import Vector3,Quaternion,PoseStamped,Twist          # 로봇의 각종 움직임 제어,
from tf.transformations import quaternion_from_euler,euler_from_quaternion  # 로봇의 위치 및 방향 좌표변환

#----------------------------------------------------


# ---------------------------------------------------------------------------- #
#                      Current position of Robot realtime update                  
# 
# 로봇의 현재좌표를 지속적으로 업데이트
#  - X-Y-Z 좌표 
#  - 로봇의 헤드 방향(Orientation)
# ---------------------------------------------------------------------------- #
def current_pose_callback(odom_data):
    global current_pose
    current_pose.pose = odom_data.pose.pose

# ---------------------------------------------------------------------------- #
#                     Current robot status realtime update                     #
# 로봇의 현재 네비게이션 상태를 지속적으로 업데이트
#  이동 중: status = 1
#  목표지점 도달: status = 3
# ---------------------------------------------------------------------------- #
def status_callback(result):
    global robot_status
    
    if result.status.status == 3:
        robot_status = True
    else:
        pass
#----------------------------------------------------
def cb_bounding_box(image_data):
    global global_x_mid
    global global_box_size
    global robot_status
    global stop_signal
    global person_detect

    global_x_mid        =  image_data.x_mid
    global_box_size     =  image_data.box_size
    #print ('box_size :',global_box_size)
    #print ('center? :',global_x_mid)
    print('person detected')
    person_detect = 1

# ---------------------------------------------------------------------------- #
def mode_converter():
    global person_detect
    global robot_status
    enough_distance = 120000

    if person_detect == 1: #사람이 검출
        if global_box_size > enough_distance: # 사람이 가까이 있을 때
            print('over box_size')
            person_detect = 0
            # 경고음
        # nav_once 0: 네비게이션 도착 전
        elif (global_box_size < enough_distance) and (rospy.get_param('nav_once') == 1): # 사람이 충분히 멀리 있고 // 도착했을 때
            rospy.set_param('mode',2)# 센트럴 라이징 모드 진입 
            if rospy.get_param('stop_signal') == 1: #멈춰라! 멈춤신호 받으면
                print('navigation mode')

                detection_image_centralize()# 중심에 맞추고 중심에 오면 #네비게이션 엑티베이트   
                rospy.set_param('mode',1)#네비게이션 모드

                rospy.set_param('stop_signal',0)
                person_detect = 0
            else: 
                pass
        else:
            pass
    else :
        print('no person')

# ---------------------------------------------------------------------------- #
def detection_image_centralize():
    rate_detection = rospy.Rate(10)
    # 로봇이 detection box의 x좌표가 중앙에 오는 것.
    # 즉, 로봇이 대상을 정면으로 볼 때까지 계속 위치제어
    while True:
        global global_x_mid
        if global_x_mid < 0.45:
            angular_velocity = 1
    
        elif global_x_mid > 0.55:
            angular_velocity = -1
        
        else :
            angular_velocity = 0

        twist.angular.x = 0
        twist.angular.y = 0
        twist.angular.z = angular_velocity
        pub_twist.publish(twist)

        print("x_mid",global_x_mid)
        if global_x_mid > 0.45 and global_x_mid < 0.55 : # xmid 가 0.5 가되면 정지
            twist.angular.x = 0
            twist.angular.y = 0
            twist.angular.z = 0
            pub_twist.publish(twist)

            rospy.set_param('navigation_status',1)
            break
        rate_detection.sleep()
        print("Centralizing_Rotating...");print('\n')

def mode_controller():
    while not rospy.is_shutdown():
        mode_converter()
        rate_main.sleep()

#-------------------------Main------------------------
if __name__ == '__main__':
    try:


    #----Initialize node & Define publisher/subscriber---
        rospy.init_node('mode_controller', anonymous=False)

        pub_twist = rospy.Publisher('cmd_vel', Twist, queue_size=10)        # 로봇의 움직임 제어
        pub_mode = rospy.Publisher('mode_control', Int64, queue_size=10)    # 모드전환

        rospy.Subscriber('/box_data',Box_data,cb_bounding_box)              # Person detection 데이터 수신
        rospy.Subscriber('/odom', Odometry, current_pose_callback)          # 로봇의 현재위치 확인

    #--------------------Setup parameter-----------------
        rospy.set_param('mode',0)                                           # 로봇의 모드값 변환
        rospy.set_param('nav_once',1)                                       # 로봇의 Navigation goal 1회지정을 위한 변수
        rospy.set_param('stop_signal',0)                                    # 로봇의 정지신호 수신

    #-------------------Define variables-----------------
        global twist                                                        # 로봇의 움직임 제어
        global robot_status                                                 # 로봇의 Navigation goal 도착여부 확인
        global current_pose                                                 # 현재 robot의 위치
        global distance_margin                                              # 정지를 위한 여유 거리
        global past_get_param                                               # 모드 전환마다 해야 할 일 분기를 위해 선언

        twist =Twist()                                                      # 제자리 회전을 위해 선언
        global_x_mid = 0                                                    # Person detection box의 x 좌표의 중앙값
        person_detect = 0                                                   # Person detection 여부
        global_box_size = 0                                                 # Person detection box의 크기값
        rate = rospy.Rate(1)                                                # while 반복 속도 제어, 1hz 
        robot_status = False                                                # 로봇의 Navigation goal 도착여부 확인
        distance_margin = 0.1                                               # 로봇의 목표값과 센서값 오차범위
        rate_main = rospy.Rate(0.5)                                         # while 반복 속도 제어, 0.5hz
        current_pose = PoseStamped()                                        # 현재 로봇의 위치 실시간 update
        past_get_param = rospy.get_param('mode')                            # Set parameter 'mode'
    #----------------Initiate main statement-------------
        mode_controller()                         # main while 문 포함

    except rospy.ROSInterruptException:
        pass
