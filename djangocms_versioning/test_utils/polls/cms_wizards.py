from cms.wizards.wizard_base import Wizard

from .forms import PollForm


class PollWizard(Wizard):
    pass


poll_wizard = PollWizard(title="Poll Wizard", weight=120, form=PollForm)
