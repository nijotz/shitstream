import imp
import os
import threading


def load_personality():
    brain = os.path.dirname(os.path.realpath(__file__))
    traits = os.listdir(brain)
    for trait in traits:
        trait_file = os.path.join(brain, trait)
        trait_name = trait.replace('.py', '')
        if not trait.startswith('__init__') and (trait.endswith('.py') or
            os.path.isdir(trait_file)):
            mod = imp.load_source(trait_name, trait_file)
            threading.Thread(target=mod.personality).start()
