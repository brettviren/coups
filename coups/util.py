# eternal mixup due to spelling versions in two ways.
def vunderify(v):
    '''
    If v is not null, return it as a vunder
    '''
    if not v or v[0] == "v":
        return v
    return "v" + v.replace(".","_")
def versionify(v):
    if not v or v[0] != "v":
        return v
    return v[1:].replace("_",".")

