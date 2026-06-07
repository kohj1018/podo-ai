import type { ApplicationAction } from '../applications.service'

export interface CreateApplicationDto {
  job_posting_id: number
  action: ApplicationAction
}
