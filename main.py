import json
from pilots import examples

if __name__=='__main__':
    print(json.dumps(examples(),indent=2,allow_nan=False))
