import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';

export interface PlanningProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  planning: {
    schedules: PlanningSchedule[]
    planningPulseRanges: PlanningPulseRanges
  }
}

interface PlanningPulseRanges {
  urgent: number
  high: number
  normal: number
  low: number
  none: number
}

interface PlanningSchedule {
  ruleId: string
  hour: string
  minute: string
  day?: string
  month?: string
  year?: string
  weekDay?: string
  timeZone?: string
}

export class PlanningContruct extends Construct {
  constructor(scope: Construct, id: string, props: PlanningProps) {
    super(scope, id);

    const planningPulseRanges = props.planning.planningPulseRanges

    const fn = new lambda.DockerImageFunction(this, 'ClickUp-Planning', {
      functionName: `ClickUp-Planning-${props.envName}`,
      code: lambda.DockerImageCode.fromImageAsset('./images/planning'),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.X86_64,
      loggingFormat: lambda.LoggingFormat.JSON,
      environment: {
        CLICKUP_API_KEY: props.clickup.apiKey,
        CLICKUP_TEAM_ID: props.clickup.teamId,
        PLANNING_PULSE_RANGE_URGENT: planningPulseRanges.urgent.toString(),
        PLANNING_PULSE_RANGE_HIGH: planningPulseRanges.high.toString(),
        PLANNING_PULSE_RANGE_NORMAL: planningPulseRanges.normal.toString(),
        PLANNING_PULSE_RANGE_LOW: planningPulseRanges.low.toString(),
        PLANNING_PULSE_RANGE_NONE: planningPulseRanges.none.toString(),
        TZ: 'America/Sao_Paulo'
      }
    });

    for (const schedule of props.planning.schedules) {
      new scheduler.Schedule(this, `Schedule-Rule-Planning-${schedule.ruleId}`, {
        scheduleName: `ClickUp-Planning-${schedule.ruleId}-${props.envName}`,
        schedule: scheduler.ScheduleExpression.cron({
          hour: schedule.hour,
          minute: schedule.minute,
          day: schedule.day,
          month: schedule.month,
          year: schedule.year,
          weekDay: schedule.weekDay,
          timeZone: cdk.TimeZone.of(schedule.timeZone ?? 'America/Sao_Paulo'),
        }),
        target: new schedulerTargets.LambdaInvoke(fn),
        timeWindow: scheduler.TimeWindow.off(),
      });
    }
  }
}
