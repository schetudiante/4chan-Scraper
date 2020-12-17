from hashlib import md5 as __md5
import base64 as __base64

"""Quick functions to hand for MD5 checking files"""

def hashHex(filepath,blocksize=65536): #65536
    """Return the MD5 hash of the file at $filepath as a string"""
    with open(filepath,'rb') as file:
        hasher = __md5()
        while len(buffer := file.read(blocksize)) > 0:
            hasher.update(buffer)
    return hasher.hexdigest()

def isHashHex(filepath,hashstr):
    """Return True if the MD5 checksum of the file at $filepath is $hashstr, else return False"""
    return hashHex(filepath) == hashstr

def base64ToHex(b64str):
    """Returns the hex equivalent of a base64 string"""
    return __base64.b64decode(b64str).hex()
