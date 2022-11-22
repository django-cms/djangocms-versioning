from cms.models import titlemodels


pagecontent_unique_together = tuple(
    set(titlemodels.PageContent._meta.unique_together) - set((("language", "page"),))
)
titlemodels.PageContent._meta.unique_together = pagecontent_unique_together
