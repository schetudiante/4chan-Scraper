
"""VCS Tools"""

def olderThan(versionx,versiony):
    """Returns True if versionx is older than versiony, else False
    Raises an exception if version types do not match"""
    versionx = [int(t) for t in versionx.split(".")]
    versiony = [int(t) for t in versiony.split(".")]
    if len(versionx) != len(versiony):
        raise Exception("Versions have different lengths")
    for i in range(len(versionx)):
        if versionx[i] < versiony[i]:
            return True
        elif versionx[i] > versiony[i]:
            return False
    return False
