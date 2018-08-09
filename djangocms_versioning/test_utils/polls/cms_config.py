from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem

from .models import PollContent

# Examples discussed with Krzysztof
#~ def answer_set(old, new):
    #~ for lold_anser in old.answer_set.all():
        #~ a = Answer(text=oold_anser.text)
        #~ a.poll_content=new
        #~ a.save()

#~ def copy_func(old):
    #~ return 

class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=PollContent,
            grouper_field_name='poll',
            #~ copy_functions={
                #~ 'answer_set': 
            #~ }
        ),
    ]
