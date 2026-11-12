import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

type RiskSurveyPromptProps = {
  /** The saved portfolio to survey, or null to keep the dialog closed. */
  portfolio: { id: string; name: string } | null
  onClose: () => void
}

export default function RiskSurveyPrompt({ portfolio, onClose }: RiskSurveyPromptProps) {
  const navigate = useNavigate()

  function start() {
    if (!portfolio) return
    onClose()
    navigate(`/portfolios/${portfolio.id}/risk-profile`)
  }

  return (
    <Dialog open={portfolio != null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Find settings that fit your goals?</DialogTitle>
          <DialogDescription>
            Answer a few short questions about your goals for {portfolio?.name ?? 'this portfolio'}.
            Optify uses your answers to recommend a strategy and limits for this portfolio only.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Not now
          </Button>
          <Button onClick={start}>Start questionnaire</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
