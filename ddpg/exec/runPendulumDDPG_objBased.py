import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['KMP_DUPLICATE_LIB_OK']='True'
dirName = os.path.dirname(__file__)
sys.path.append(os.path.join(dirName, '..'))
sys.path.append(os.path.join(dirName, '..', '..'))
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)
import gym
from functionTools.loadSaveModel import saveVariables
import matplotlib.pyplot as plt
import tensorflow as tf

from src.objBased.ddpg_objBased import GetActorNetwork, Actor, GetCriticNetwork, Critic, ActOneStep, MemoryBuffer, \
    SaveModel, TrainDDPGWithGym, LearnFromBuffer, reshapeBatchToGetSASR, TrainDDPGModelsOneStep
from environment.noise.noise import ExponentialDecayGaussNoise


def main():
    env_name = 'Pendulum-v0'
    env = gym.make(env_name)

    hyperparamDict = dict()
    hyperparamDict['actorHiddenLayersWidths'] = [256]
    hyperparamDict['actorActivFunction'] = [tf.nn.relu]* len(hyperparamDict['actorHiddenLayersWidths'])+ [tf.nn.tanh]
    hyperparamDict['actorHiddenLayersWeightInit'] = [tf.random_uniform_initializer(minval=0, maxval=0.3) for units in hyperparamDict['actorHiddenLayersWidths']]
    hyperparamDict['actorHiddenLayersBiasInit'] = [tf.constant_initializer(0.1) for units in hyperparamDict['actorHiddenLayersWidths']]
    hyperparamDict['actorOutputWeightInit'] = tf.random_uniform_initializer(minval=0, maxval=0.3)
    hyperparamDict['actorOutputBiasInit'] = tf.constant_initializer(0.1)
    hyperparamDict['actorLR'] = 0.001

    hyperparamDict['criticHiddenLayersWidths'] = [256]
    hyperparamDict['criticActivFunction'] = [tf.nn.relu]* len(hyperparamDict['criticHiddenLayersWidths'])+ [None]
    hyperparamDict['criticHiddenLayersWeightInit'] = [tf.random_uniform_initializer(minval=0, maxval=0.1) for units in hyperparamDict['criticHiddenLayersWidths']]
    hyperparamDict['criticHiddenLayersBiasInit'] = [tf.constant_initializer(0.1) for units in hyperparamDict['criticHiddenLayersWidths']]
    hyperparamDict['criticOutputWeightInit'] = tf.random_uniform_initializer(minval=0, maxval=0.1)
    hyperparamDict['criticOutputBiasInit'] = tf.constant_initializer(0.1)
    hyperparamDict['criticLR'] = 0.001

    hyperparamDict['tau'] = 0.01
    hyperparamDict['gamma'] = 0.9
    hyperparamDict['gradNormClipValue'] = 5

    hyperparamDict['maxEpisode'] = 200
    hyperparamDict['maxTimeStep'] = 200
    hyperparamDict['bufferSize'] = 1e4
    hyperparamDict['minibatchSize'] = 128

    hyperparamDict['noiseInitVariance'] = 3
    hyperparamDict['varianceDiscount'] = .9995
    hyperparamDict['noiseDecayStartStep'] = hyperparamDict['bufferSize']
    hyperparamDict['minVar'] = .1
    hyperparamDict['normalizeEnv'] = False

    actionHigh = env.action_space.high
    actionLow = env.action_space.low
    actionBound = (actionHigh - actionLow)/2

    session = tf.Session()
    stateDim = env.observation_space.shape[0]
    actionDim = env.action_space.shape[0]
    getActorNetwork = GetActorNetwork(hyperparamDict, batchNorm= False)
    actor = Actor(getActorNetwork, stateDim, actionDim, session, hyperparamDict, agentID= None, actionRange=actionBound)

    getCriticNetwork = GetCriticNetwork(hyperparamDict, addActionToLastLayer = True, batchNorm = False)
    critic = Critic(getCriticNetwork, stateDim, actionDim, session, hyperparamDict)

    saver = tf.train.Saver(max_to_keep=None)
    tf.add_to_collection("saver", saver)
    session.run(tf.global_variables_initializer())

    fileName = 'ddpg_mujoco_Pendulum_normalized_confirm'
    modelSavePath = os.path.join(dirName, '..', 'trainedModels', fileName)
    modelSaveRate = 500
    saveModel = SaveModel(modelSaveRate, saveVariables, modelSavePath, session)

    trainDDPGOneStep = TrainDDPGModelsOneStep(reshapeBatchToGetSASR, actor, critic)
    learningStartBufferSize = hyperparamDict['minibatchSize']
    learnFromBuffer = LearnFromBuffer(learningStartBufferSize, trainDDPGOneStep, learnInterval=1)
    buffer = MemoryBuffer(hyperparamDict['bufferSize'], hyperparamDict['minibatchSize'])

    noise = ExponentialDecayGaussNoise(hyperparamDict['noiseInitVariance'], hyperparamDict['varianceDiscount'], hyperparamDict['noiseDecayStartStep'], hyperparamDict['minVar'])
    actOneStep = ActOneStep(actor, actionLow, actionHigh)
    ddpg = TrainDDPGWithGym(hyperparamDict['maxEpisode'], hyperparamDict['maxTimeStep'], buffer, noise, actOneStep, learnFromBuffer, env, saveModel)

    episodeRewardList = ddpg()
    plt.plot(range(len(episodeRewardList)), episodeRewardList)
    plt.show()

if __name__ == '__main__':
    main()