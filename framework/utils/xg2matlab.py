def cvt(oldfile):
    """
    Convert xgraph files from SPLIB into Matlab-executable plot files.
    """
    import re
    try:
        of = open(oldfile,'r')
    except:
        print 'Unable to open file ' + oldfile
        return None
    try:
        newfile = oldfile + '.m'
        nf = open(newfile, 'w')
    except:
        print 'Unable to open output file ' + newfile
        return None

    first = True

    cruft = []
    curves = []
    legend = 'legend('
    for line in of:
        phrases = line.split(': ')
        blurb0 = phrases[0]
        blurb0 = blurb0.replace('\n', '')

        if blurb0 == '':  # Blank line
            nf.write('\n')
            continue

        if blurb0[0] != '"':

            if blurb0[0] != ' ': # Not a blank, ", or space. Must be title or values
                if blurb0 == 'TitleText':
                    cmd = "title('" + phrases[1].replace("\n",'') + "');"
                    cruft.append(cmd)
                else:
                    if blurb0 == 'XUnitText':
                        cmd = "xlabel('" + phrases[1].replace("\n",'') + "');"
                        cruft.append(cmd)
                    else:
                        if blurb0 == 'YUnitText':
                            cmd = "ylabel('" + phrases[1].replace("\n",'') + "');"
                            cruft.append(cmd)
                nf.write('\n')
            else:  # Not a double quote, but does have leading blank. Must be data.
                blurb0.replace(' ','')
                nf.write(str(blurb0))
                nf.write('\n')

        else: # first character is dq
            if not first :
                nf.write(' ]; \n')
            else:
                first = False
            curvename = phrases[0].strip()
            curvename = curvename.replace('(', '')
            curvename = curvename.replace(')', '')
            curvename = curvename.replace(' ', '')
            curvename = curvename.replace('"', '')
            curvename = curvename.replace('/', 'and')
            nf.write(curvename)
            nf.write(' = [ ... \n')
            curves.append(curvename)

    nf.write(' ]; \n')
    cmd = 'semilogy('

    for c in curves:
        legend = legend + "'" + c + "'"
        cmd = cmd + c + '(:,1), ' + c + '(:,2)'
        if c != curves[-1]:
            cmd = cmd + ', '
            legend = legend + ', '

    cmd = cmd + ');\n'
    nf.write(cmd)
    nf.write(legend + ');\n')

    for s in cruft:
        nf.write(s)
        nf.write('\n')

    of.close()
    nf.close()
    return newfile
    


if __name__ == '__main__':
    cvt('resi')
