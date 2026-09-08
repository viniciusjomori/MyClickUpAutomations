import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as schedulerTargets from 'aws-cdk-lib/aws-scheduler-targets';

export interface AntiProcastinationProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  workdayOnlySpaceIds?: string[],
  intertexto: {
    apiKey: string,
    state: string
  },
  smtp: {
    host: string,
    port: number,
    username?: string,
    password?: string,
    useTls?: boolean,
    name?: string,
    from: string,
    to: string[]
  },
  antiProcastination: {
    daysBeforeAdvice: DaysBeforeAdvice,
    schedules: AntiProcastinationSchedule[]
  }
}

interface DaysBeforeAdvice {
  urgent: number
  high: number
  normal: number
  low: number
  none: number
}

interface AntiProcastinationSchedule {
  ruleId: string
  hour: string
  minute: string
  day?: string
  month?: string
  year?: string
  weekDay?: string
  timeZone?: string
}

export class AntiProcastinationContruct extends Construct {
  constructor(scope: Construct, id: string, props: AntiProcastinationProps) {
    super(scope, id);

    if (props.antiProcastination.schedules.length === 0) {
      return;
    }

    const table = new dynamodb.Table(this, 'ClickUp-AntiProcastination-Tasks', {
      tableName: `ClickUp-AntiProcastination-Tasks-${props.envName}`,
      partitionKey: {
        name: 'task_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const fn = new lambda.DockerImageFunction(this, 'ClickUp-AntiProcastination', {
      functionName: `ClickUp-AntiProcastination-${props.envName}`,
      code: lambda.DockerImageCode.fromImageAsset('./images/antiProcastination'),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.X86_64,
      loggingFormat: lambda.LoggingFormat.JSON,
      environment: {
        CLICKUP_API_KEY: props.clickup.apiKey,
        CLICKUP_TEAM_ID: props.clickup.teamId,
        ANTI_PROCASTINATION_WORKDAY_ONLY_SPACE_IDS: (props.workdayOnlySpaceIds ?? []).join(','),
        ANTI_PROCASTINATION_TABLE_NAME: table.tableName,
        ANTI_PROCASTINATION_DAYS_BEFORE_ADVICE_URGENT: props.antiProcastination.daysBeforeAdvice.urgent.toString(),
        ANTI_PROCASTINATION_DAYS_BEFORE_ADVICE_HIGH: props.antiProcastination.daysBeforeAdvice.high.toString(),
        ANTI_PROCASTINATION_DAYS_BEFORE_ADVICE_NORMAL: props.antiProcastination.daysBeforeAdvice.normal.toString(),
        ANTI_PROCASTINATION_DAYS_BEFORE_ADVICE_LOW: props.antiProcastination.daysBeforeAdvice.low.toString(),
        ANTI_PROCASTINATION_DAYS_BEFORE_ADVICE_NONE: props.antiProcastination.daysBeforeAdvice.none.toString(),
        INVERTEXTO_API_KEY: props.intertexto.apiKey ?? '',
        INVERTEXTO_STATE: props.intertexto.state ?? '',
        SMTP_HOST: props.smtp.host,
        SMTP_PORT: props.smtp.port.toString(),
        SMTP_USERNAME: props.smtp.username ?? '',
        SMTP_PASSWORD: props.smtp.password ?? '',
        SMTP_USE_TLS: (props.smtp.useTls ?? true).toString(),
        SMTP_NAME: props.smtp.name ?? '',
        SMTP_FROM: props.smtp.from,
        SMTP_TO: props.smtp.to.join(','),
        TZ: 'America/Sao_Paulo'
      }
    });

    table.grantReadWriteData(fn);

    for (const schedule of props.antiProcastination.schedules) {
      new scheduler.Schedule(this, `Schedule-Rule-AntiProcastination-${schedule.ruleId}`, {
        scheduleName: `ClickUp-AntiProcastination-${schedule.ruleId}-${props.envName}`,
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
