#!bin/env python

import ConfigParser
import glob
import os
from subprocess import call, PIPE, Popen
import sys
import traceback

# Controls if commandline also goes to screen
# This will not include IO just commandline
fLog  = True

# Constants
c_sCommandLineScripts = "CommandlineScripts"
c_sCopyright = "Copyright"
c_sCopyrightYear = "CopyrightYear"
c_sDependencies = "Dependencies"
c_sDescription = "Description(<60char)"
c_sDescriptionLong = "Description(Longer)"
c_sEmail = "Email"
c_sRepository = "Repository"
c_cScriptDelimiter = ","
c_sSep = os.path.sep
c_sSectionHeader = "Tool"
c_sToolName = "Name"
c_sVersion = "Version(Tag)"
c_sWebpage = "Webpage"

def funcDoCommands( aastrCommands, fVerbose = False, fForced = False, fPiped = False ):
  """ Act on a list of commands. If the handle is not a none then
      use it to write to a file / out. Otherwise execute the commands. 

      Standard commands should be a list of lists with the internal lists each word of the command [["mkdir","newDir"],["rm","-r","newDir"]]
      Forced commands should be a List of commands as strings [["mkdir newDir"],["rm -r newDir"]]
      Piped commands which are forced should be List of lists which are pairs, the first string command being piped into the second.
        This is very rudimentary but all that was needed. [["cat newFile", "less -S"]]
      Piped commands which are not forced were not implemented because they are so far not needed.
 """

  #Run command
  try:
    for astrCommand in aastrCommands:
      if fVerbose:
        print( " ".join( astrCommand ) )

      ## The return code to indicate an error in the process.
      iReturnCode = None
      if fForced:
        if fPiped:
          subpPiped = Popen( astrCommand[1], stdin = PIPE, shell = True )
          iReturnCode, ignore = subpPiped.communicate( astrCommand[0] )
        else:
          iReturnCode = Popen(astrCommand, shell = True)
      elif fPiped:
          print("Piped and Forced calls not needed.")
      else:
        iReturnCode = call( astrCommand )

      if fVerbose:
        print "Return=" + str( iReturnCode )
      if iReturnCode > 0:
        print "Error:: Error during command call. Script stopped."
        print "Error:: Error Code " + str( iReturnCode ) + "."
        print "Error:: Command =" + str( astrCommand ) + "."
        return False
  except ( OSError, TypeError ), e: 
    print "Error:: Error during command call. Script stopped."
    print "Error:: Command =" + str( astrCommand ) + "."
    print "Error:: OS error: " + str( traceback.format_exc( e ) ) + "."
    return False
  return True


# Configuration
c_sBiobakeryInstallLocation = c_sSep + "usr" + c_sSep + "share" + c_sSep

# Get all files with glob
lsConfigFiles = glob.glob("*.bread")

# Config parser
cprsr = ConfigParser.ConfigParser(allow_no_value=True)

# Parse the Config files
for sConfigFile in lsConfigFiles:

  print("Making Bread: "+sConfigFile)

  cprsr.read(sConfigFile)

  # Current tool name
  sToolName = cprsr.get( c_sSectionHeader, c_sToolName)

  # Get the version
  sVersion = cprsr.get( c_sSectionHeader, c_sVersion )

  # Get scripts to install / remove with the post scripts
  sScripts = cprsr.get( c_sSectionHeader, c_sCommandLineScripts )
  lsScripts = [ sScript.strip() for sScript in sScripts.split( c_cScriptDelimiter ) ]

  # Global variables
  sInstallDir = c_sBiobakeryInstallLocation + "biobakery" + c_sSep

  # Get the project directory given the tag specified by the version
  fSuccess = funcDoCommands( [[ "hg", "clone", "-r", sVersion, cprsr.get( c_sSectionHeader, c_sRepository ) ]], fVerbose = fLog )
  if not fSuccess: exit(1)

  # Make the directory for the project
  sProjectDir = "-".join( [ sToolName, sVersion ] )
  fSuccess = funcDoCommands( [[ "mkdir", sProjectDir ]], fVerbose = fLog)
  if not fSuccess: exit(1)

  # Make scripts into compressed archive
  # Move the scripts into the package
#  sToolFileToArchive = sProjectDir.replace("-","_") + ".orig"
#  sToolArchiveName = sToolFileToArchive + ".tar.gz"
#  fSuccess = funcDoCommands( [["mv", sToolName, sToolFileToArchive],
#                              [ "tar", "-zcvf", sToolArchiveName, sToolFileToArchive ],
#                              [ "mv", sToolArchiveName, sProjectDir ],
#                              [ "rm", "-r", sToolFileToArchive]], fVerbose = fLog)

  fSuccess = funcDoCommands( [[ "mv", sToolName, sProjectDir + c_sSep + sToolName ]], fVerbose = fLog)

  if not fSuccess: exit(1)

  # Make a default project
  # -n program is debian native
  # -s package class is single
  # -e maintainer email address
  os.chdir( sProjectDir )
  fSuccess = funcDoCommands( [[ "yes", "dh_make -n -s -e " + cprsr.get( c_sSectionHeader, c_sEmail ) ]], fForced = True, fPiped = True, fVerbose = fLog)
  if not fSuccess: exit(1)

  # Make the settings file
  with open( "debian"+ c_sSep + sToolName + ".install", "w" ) as hndlInstall:
    hndlInstall.write(sToolName + " " + c_sBiobakeryInstallLocation + sProjectDir)

  # Update dependencies
  fSuccess = funcDoCommands( [[ "sed", "-i", "s/Build-Depends.*$/Build-Depends: " + cprsr.get( c_sSectionHeader, c_sDependencies ) + "/", "debian" + c_sSep + "control" ],
                    [ "sed", "-i", "s/Homepage.*$/Homepage: " + cprsr.get( c_sSectionHeader, c_sWebpage ).replace("/","\\/") + "/", "debian/control" ],
                    [ "sed", "-i", "s/Description.*$/Description: " + cprsr.get( c_sSectionHeader, c_sDescription ).replace("/","\\/") + "/", "debian/control" ],
                    [ "sed", "-i", "s/ <insert long description.*$/ " + cprsr.get( c_sSectionHeader, c_sDescriptionLong ).replace("/","\\/") + "/", "debian" + c_sSep + "control" ]], fVerbose = fLog )
  if not fSuccess: exit(1)
  
  # Update the license information
  with open( "debian" + c_sSep + "copyright", "w") as hndlCopyRight:
    hndlCopyRight.write("Format: http://dep.debian.net/deps/dep5\n")
    hndlCopyRight.write("Upstream-Name: " + sProjectDir + "\n")
    hndlCopyRight.write("Source: <" + cprsr.get( c_sSectionHeader, c_sWebpage ) + ">\n\n")
    hndlCopyRight.write("Files: *\n")
    hndlCopyRight.write("Copyright: <years> <put author name and email here>\n")
    hndlCopyRight.write("           <years> <likewise for another author>\n")
    hndlCopyRight.write("License: GPL-3.0+\n\n")
    hndlCopyRight.write("Files: debian/*\n")
    hndlCopyRight.write("Copyright: " + cprsr.get( c_sSectionHeader, c_sCopyrightYear ) + " " + cprsr.get( c_sSectionHeader, c_sCopyright ) + "\n")
    hndlCopyRight.write("License: MIT\n\n")
    hndlCopyRight.write("#####################################################################################\n")
    hndlCopyRight.write("#Copyright (C) <" + cprsr.get( c_sSectionHeader, c_sCopyrightYear ) + ">\n#\n")
    hndlCopyRight.write("#Permission is hereby granted, free of charge, to any person obtaining a copy of\n")
    hndlCopyRight.write("#this software and associated documentation files (the \"Software\"), to deal in the\n")
    hndlCopyRight.write("#Software without restriction, including without limitation the rights to use, copy,\n")
    hndlCopyRight.write("#modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,\n")
    hndlCopyRight.write("#and to permit persons to whom the Software is furnished to do so, subject to\n")
    hndlCopyRight.write("#the following conditions:\n#\n")
    hndlCopyRight.write("#The above copyright notice and this permission notice shall be included in all copies\n")
    hndlCopyRight.write("#or substantial portions of the Software.\n#\n")
    hndlCopyRight.write("#THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,\n")
    hndlCopyRight.write("#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A\n")
    hndlCopyRight.write("#PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT\n")
    hndlCopyRight.write("#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION\n")
    hndlCopyRight.write("#OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE\n")
    hndlCopyRight.write("#SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n")
    hndlCopyRight.write("#####################################################################################")

  # Make the post install script
  if( len( lsScripts ) > 0 ):
    with open( "debian" + c_sSep + "postinst", "w") as hndlPostInst:
      hndlPostInst.write("#!" + c_sSep + "bin" + c_sSep + "env bash\n")
      hndlPostInst.write("set -e\n\n")
      hndlPostInst.write("case \"\$1\" in\n")
      hndlPostInst.write("    configure)\n")
      for sScript in lsScripts:
        hndlPostInst.write("      ln -s " + c_sBiobakeryInstallLocation + sProjectDir + c_sSep + sScript + " " + c_sSep + "usr" + c_sSep + "bin" + c_sSep + sScript.split(os.path.sep)[-1] + " \n")
      hndlPostInst.write("    ;;\n\n")
      hndlPostInst.write("    abort-upgrade|abort-remove|abort-deconfigure)\n    ;;\n\n")
      hndlPostInst.write("    *)\n")
      hndlPostInst.write("        echo \"postinst called with unknown argument '\$1'\" >&2\n")
      hndlPostInst.write("        exit 1\n    ;;\nesac")
      hndlPostInst.write("#DEBHELPER#\n\n")
      hndlPostInst.write("exit 0")

    # Make the post remove script
    with open( "debian" + c_sSep + "postrm", "w") as hndlPostRM:
      hndlPostRM.write("#!" + c_sSep + "bin" + c_sSep + "env bash")
      hndlPostRM.write("set -e\n\n")
      hndlPostRM.write("case \"\$1\" in\n    remove)")
      for sScript in lsScripts:
        hndlPostRM.write("rm " + c_sSep + "usr" + c_sSep + "bin" + c_sSep + sScript + "\n    ;;\n\n")
      hndlPostRM.write("    purge|upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)\n    ;;\n\n")
      hndlPostRM.write("    *)\n")
      hndlPostRM.write("        echo \"postrm called with unknown argument '\$1'\" >&2\n")
      hndlPostRM.write("        exit 1\n    ;;\nesac\n#DEBHELPER#\n\nexit 0")

  # Build package
  fSuccess = funcDoCommands( [[ "dpkg-buildpackage", "-us", "-uc" ]], fVerbose = fLog )
  if not fSuccess: exit(1)