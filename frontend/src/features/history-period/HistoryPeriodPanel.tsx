import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

type HistoryPeriodPanelProps = {
  startDate: string
  endDate: string
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
}

export default function HistoryPeriodPanel({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: HistoryPeriodPanelProps) {
  return (
    <div className="space-y-4">
      <FieldGroup className="grid gap-4 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="start-date">Start date</FieldLabel>
          <Input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(event) => onStartDateChange(event.target.value)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="end-date">End date</FieldLabel>
          <Input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(event) => onEndDateChange(event.target.value)}
          />
        </Field>
      </FieldGroup>
      <FieldDescription>
        Example: about one year of history ending today. Prices load automatically when you run
        analysis. Stored bars are reused when they already cover the range.
      </FieldDescription>
    </div>
  )
}
