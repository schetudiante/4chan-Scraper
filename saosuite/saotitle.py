
"""Title with subtitle, and my SAO logo in Unicode blocks"""

_full =   "\u2588"
_top =    "\u2580"
_bottom = "\u2584"
_space = " "

logo_raw = [
    "ABBBABABBABABBBA",
    "AEEAADAAAADAAEEA",
    "AEEAEACIICAEAEEA",
    "ABBBAIIIIIIABBBA",
    "ABBBAIIIIIIABBBA",
    "AEEEABGIIGBAEEEA",
    "AEABADAAAADABAEA",
    "ADADDDDDDDDDDADA"]

logo_frameLayer = [line.replace("A",_full).replace("B",_top).replace("C",_top).replace("D",_bottom).replace("E",_space).replace("F",_space).replace("G",_bottom).replace("H",_space).replace("I",_space) for line in logo_raw]

logo_extrasLayer = [line.replace("A",_space).replace("B",_bottom).replace("C",_space).replace("D",_top).replace("E",_full).replace("F",_top).replace("G",_space).replace("H",_bottom).replace("I",_space) for line in logo_raw]

logo_centreLayer = [line.replace("A",_space).replace("B",_space).replace("C",_bottom).replace("D",_space).replace("E",_space).replace("F",_bottom).replace("G",_top).replace("H",_top).replace("I",_full) for line in logo_raw]

logo_bw = [line.replace("A",_full).replace("B",_top).replace("C",_top).replace("D",_bottom).replace("E",_space).replace("F",_space).replace("G",_bottom).replace("H",_space).replace("I",_space) for line in logo_raw]

def logoTitle(title="SAO Title",subtitle="Lorem Ipsum"):
    plen = max(len(title),len(subtitle))
    listLogoTitle = []
    listLogoTitle.append(logo_bw[0])
    listLogoTitle.append(logo_bw[1])
    listLogoTitle.append(logo_bw[2]+"  "+      "".center(plen,"~"))
    listLogoTitle.append(logo_bw[3]+"  "+   title.center(plen,"~"))
    listLogoTitle.append(logo_bw[4]+"  "+subtitle.center(plen,"~"))
    listLogoTitle.append(logo_bw[5]+"  "+      "".center(plen,"~"))
    listLogoTitle.append(logo_bw[6])
    listLogoTitle.append(logo_bw[7])
    return listLogoTitle

def printLogoTitle(title="SAO Title",subtitle="Lorem Ipsum",newline=True):
    for line in logoTitle(title,subtitle):
        print(line)
    if newline is True:
        print()

if __name__ == "__main__":
    printLogoTitle()
    input()
