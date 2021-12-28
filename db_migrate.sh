#!/bin/bash

echo "get the ecs ec2 instance ids"
ecs_instance_ids=$(aws ecs list-container-instances --cluster $ECS_CLUSTER --query 'containerInstanceArns[*]' --output text)
echo "instance ids" $ecs_instance_ids

echo "setting desired count to 0"
ecs_set=$(aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --desired-count 0)

echo "get the tasks count"
task_count=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE --query 'taskArns[*]' --output text | wc -l)
echo "task count" $task_count

if [ $task_count -gt 0 ]; then
  echo "get list of task arns"
  task_arns=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE --query 'taskArns[*]' --output text)
  echo "task arns" $task_arns

  echo "stop all tasks"
  aws ecs stop-task --cluster $ECS_CLUSTER --task $task_arns
fi

echo "get the tasks count"
task_count=$(aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE --query 'taskArns[*]' --output text | wc -l)
echo "task count" $task_count

if [ $task_count -eq 0 ]; then
  echo "no tasks to stop"
  start_task=$(aws ecs start-task --cluster $ECS_CLUSTER --container-instances $ecs_instance_ids \
  --task-definition $TASK_DEFINITION \
  --overrides '{"containerOverrides":[{"name":"test","command":["./deploy.sh"]}]}' --query 'tasks[0].taskArn' --output text)

  state=0
  while [ $state -eq 0 ]; do
    echo "sleep 30 seconds"
    sleep 30
    echo "check if task is running"
    task_status=$(aws ecs describe-tasks --cluster $ECS_CLUSTER --tasks $start_task --query 'tasks[0].lastStatus' --output text)
    echo "task status" $task_status
    if [ "$task_status" = "STOPPED" ]; then
      echo "task stopped"
      break
    else
      echo "codepipeline to wait for task to stop"  
    fi
  done
else
  echo "unable to stop tasks"
  exit 1
fi

echo "setting desired count to $task_count"
aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --desired-count $task_count