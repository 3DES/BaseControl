#!/usr/bin/python3


import argparse


from Base.ProjectRunner import ProjectRunner


'''
project main function
'''
if __name__ == '__main__':
    initFileName = 'init.json'
    
    # handle command line arguments
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("-i", "--init", dest = initFileName, help = "use this init file instead of init.json")
    arguments = argumentParser.parse_args()
    
    ProjectRunner.executeProject(initFileName)
    
