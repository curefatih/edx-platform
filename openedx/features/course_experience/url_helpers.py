"""
Helper functions for logic related to learning (courseare & course home) URLs.

Centralizdd in openedx/features/course_experience instead of lms/djangoapps/courseware
because the Studio course outline may need these utilities.
"""
from django.conf import settings
from django.urls import reverse
from six.moves.urllib.parse import urlencode

from lms.djangoapps.courseware.toggles import courseware_mfe_is_active
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.search import navigation_index, path_to_location


def get_courseware_url(usage_key, request=None):
    """
    Return the URL to the canonical learning experience for a given block.

    We choose between either the Legacy or Learning MFE depending on the
    course that the block is in, the requesting user, and the state of
    the 'courseware' waffle flags.

    Raises:
        * ItemNotFoundError if no data at the usage_key.
        * NoPathToItem if location not in any class.

    Args:
        usage_key (UsageKey|str)
        request (Request)
    """
    (
        course_key,
        section_id,
        sequence_id,
        unit_id,
        position,
        final_target_id,
    ) = path_to_location(modulestore(), usage_key, request)
    if courseware_mfe_is_active(course_key):
        return get_learning_mfe_courseware_url(
            course_key,
            sequence_id,
            unit_id,
        )
    else:
        return _get_legacy_courseware_url(
            course_key,
            section_id,
            sequence_id,
            position,
            final_target_id,
        )


def get_legacy_courseware_url(course_key, usage_key, request=None):
    """
    TODO
    """
    (
        course_key,
        section_id,
        sequence_id,
        _unit_id,
        position,
        final_target_id,
    ) = path_to_location(modulestore(), usage_key, request)
    return _get_legacy_courseware_url(
        course_key,
        section_id,
        sequence_id,
        position,
        final_target_id,
    )


def _get_legacy_courseware_url(
        course_key,
        section_id,
        sequence_id,
        position,
        final_target_id,
):
    """
    Return a str with the URL for the specified legacy (LMS-rendered) courseware content.

    Args:
        course_key (CourseKey|str)
        section_id (str)
        sequence_id (str)
        position (str)
        final_target_id

    Returns:
        Redirect url string
    """
    # choose the appropriate view (and provide the necessary args) based on the
    # args provided by the redirect.
    # Rely on index to do all error handling and access control.
    course_id = str(course_key)
    if not section_id:
        redirect_url = reverse('courseware', args=(course_id, ))
    elif not sequence_id:
        redirect_url = reverse('courseware_chapter', args=(course_id, section_id))
    elif not position:
        redirect_url = reverse(
            'courseware_section',
            args=(course_id, section_id, sequence_id),
        )
    else:
        # Here we use the navigation_index from the position returned from
        # path_to_location - we can only navigate to the topmost vertical at the
        # moment
        redirect_url = reverse(
            'courseware_position',
            args=(course_id, section_id, sequence_id, navigation_index(position))
        )
    redirect_url += "?{}".format(urlencode({'activate_block_id': str(final_target_id)}))
    return redirect_url


def get_learning_mfe_courseware_url(course_key, sequence_id=None, unit_id=None):
    """
    Return a str with the URL for the specified courseware content in the Learning MFE.

    The micro-frontend determines the user's position in the vertical via
    a separate API call, so all we need here is the course_key, section, and
    vertical IDs to format it's URL. For simplicity and performance reasons,
    this method does not inspect the modulestore to try to figure out what
    Unit/Vertical a sequence is in. If you try to pass in a unit_key without
    a sequence_key, the value will just be ignored and you'll get a URL pointing
    to just the course_key.

    It is also capable of determining our section and vertical if they're not
    present.  Fully specifying it all is preferable, though, as the
    micro-frontend can save itself some work, resulting in a better user
    experience.

    We're building a URL like this:

    http://localhost:2000/course/course-v1:edX+DemoX+Demo_Course/block-v1:edX+DemoX+Demo_Course+type@sequential+block@19a30717eff543078a5d94ae9d6c18a5/block-v1:edX+DemoX+Demo_Course+type@vertical+block@4a1bba2a403f40bca5ec245e945b0d76

    `course_key`, `sequence_key`, and `unit_key` can be either OpaqueKeys or
    strings. They're only ever used to concatenate a URL string.
    """
    mfe_link = '{}/course/{}'.format(settings.LEARNING_MICROFRONTEND_URL, course_key)
    if sequence_id:
        mfe_link += '/{}'.format(sequence_id)
        if unit_id:
            mfe_link += '/{}'.format(unit_id)
    return mfe_link


def get_learning_mfe_home_url(course_key, view_name=None):
    """
    Given a course run key and view name, return the appropriate course home (MFE) URL.

    We're building a URL like this:

    http://localhost:2000/course/course-v1:edX+DemoX+Demo_Course/dates

    `course_key` can be either an OpaqueKey or a string.
    `view_name` is an optional string.
    """
    mfe_link = f'{settings.LEARNING_MICROFRONTEND_URL}/course/{course_key}'

    if view_name:
        mfe_link += f'/{view_name}'

    return mfe_link


def is_request_from_learning_mfe(request):
    """
    Returns whether the given request was made by the frontend-app-learning MFE.
    """
    return (
        settings.LEARNING_MICROFRONTEND_URL and
        request.META.get('HTTP_REFERER', '').startswith(settings.LEARNING_MICROFRONTEND_URL)
    )
