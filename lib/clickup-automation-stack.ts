import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { BackupContruct } from './constructs/backup';
import { AntiProcastinationContruct } from './constructs/anti-procastination';
import { CurrentizeContruct } from './constructs/currentize';
import { DeleteOldEmptyTasksContruct } from './constructs/delete-old-empty-tasks';
import { PlanningContruct } from './constructs/planning';
import { RemindMeLaterContruct } from './constructs/remind-me-later';
import { TagArchiveContruct } from './constructs/tag-archive';

export interface ClickUpAutomationProps extends cdk.StackProps {
  envName: string,
  clickup: {
    apiKey: string,
    teamId: string
  },
  workdayOnlySpaceIds?: string[],
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
    strikeQnt: {
      urgent: number,
      high: number,
      normal: number,
      low: number,
      none: number
    },
    schedules: {
      ruleId: string,
      hour: string,
      minute: string,
      day?: string,
      month?: string,
      year?: string,
      weekDay?: string,
      timeZone?: string
    }[]
  },
  backup: {
    schedules: {
      ruleId: string,
      hour: string,
      minute: string,
      day?: string,
      month?: string,
      year?: string,
      weekDay?: string,
      timeZone?: string
    }[]
  },
  currentize: {
    schedules: {
      ruleId: string,
      hour: string,
      minute: string,
      day?: string,
      month?: string,
      year?: string,
      weekDay?: string,
      timeZone?: string
    }[]
  },
  deleteOldEmptyTasks: {
    days: number,
    ignoredSpaceIds?: string[],
    schedules: {
      ruleId: string,
      hour: string,
      minute: string,
      day?: string,
      month?: string,
      year?: string,
      weekDay?: string,
      timeZone?: string
    }[]
  },
  planning: {
    nextTaskTooFarAwayRanges: {
      urgent: number,
      high: number,
      normal: number,
      low: number,
      none: number
    },
    schedules: {
      ruleId: string,
      hour: string,
      minute: string,
      day?: string,
      month?: string,
      year?: string,
      weekDay?: string,
      timeZone?: string
    }[]
  },
  intertexto: {
    apiKey: string,
    state: string
  },
  tagArchive: {
    ruleId: string,
    tag: string,
    archive: {
      hour: string,
      minute: string
    },
    unarchive: {
      hour: string,
      minute: string
    },
    weekDay: string,
    holidays?: 'ignore' | 'consider' | null,
    timeZone?: string
  }[],
  remindMeLater: {
    period: {
      hour: string,
      minute: string,
      weekDay?: string,
      timeZone?: string
    },
    tags: {
      tag: string,
      delayMinutes: number
    }[]
  }
}

export class ClickUpAutomationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ClickUpAutomationProps) {
    super(scope, id, props);

    new AntiProcastinationContruct(this, 'AntiProcastinationConstruct', props)
    new BackupContruct(this, 'BackupConstruct', props)
    new CurrentizeContruct(this, 'CurrentizeConstruct', props)
    new DeleteOldEmptyTasksContruct(this, 'DeleteOldEmptyTasksConstruct', props)
    new PlanningContruct(this, 'PlanningConstruct', props)
    new TagArchiveContruct(this, 'TagArchiveConstruct', props)
    new RemindMeLaterContruct(this, 'RemindMeLaterConstruct', props)

  }
}
