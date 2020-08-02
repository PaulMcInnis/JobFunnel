# NOTE: Setting job's status to these moves the job from masterlist -> deny list
REMOVE_STATUSES = ['archive', 'archived', 'remove', 'rejected']
CSV_HEADER = [
    'status', 'title', 'company', 'location', 'date', 'blurb', 'tags', 'link',
    'id', 'provider', 'query', 'locale'
]  # TODO: need to add short and long descriptions (breaking change)
