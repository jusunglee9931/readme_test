import argparse
import mnist_input_data
import tensorflow as tf
import numpy as np
import mnist_input_data
import PIL
import matplotlib.pyplot as plt
import math
'''
global variable for simplicity

'''
img_size = 64
z_size = 100

g_gs = np.random.uniform(-1. , 1., (25,1,1,z_size)).astype(np.float32) 
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-steps', type=int, default=100,
                        help='the number of training steps to take')
    parser.add_argument('--batch-size', type=int, default=25,
                        help='the batch size')
    parser.add_argument('--learning-rate', type=float, default = 0.0002,
                        help='learning rate')
    parser.add_argument('--eval', action='store_true',
                        help='eval mode') 
    parser.add_argument('--save', action='store_true',
                        help='save on')
    parser.add_argument('--mnist-folder', type= str,default ='MNIST_data',
                         help='mnist dataset folder name')
    return parser.parse_args()



def generateimage(m,sess,e,new=False):
       if new :
        gs = np.random.uniform(-1. , 1., (m.bn,1,1,z_size)).astype(np.float32) 
        g = sess.run(m.g, {m.in_ph : gs})
       else :
        g = sess.run(m.g,{m.in_ph :  g_gs})
       g = g.reshape(m.bn,img_size,img_size)
       #print(g)
       fig = plt.figure(figsize=(img_size,img_size),tight_layout=True)
       grid = math.sqrt(m.bn)
       for i in range(m.bn):
        ax = fig.add_subplot(grid,grid,i+1)
        ax.set_axis_off()
        plt.imshow(g[i],shape=(64,64),cmap='Greys_r')
       plt.savefig("dc_gan_figure_epoch%s" %e)
       plt.close()


'''
m  =model

'''

def drawlossplot( m,loss_g,loss_d,e):
    print(loss_g)
    g_x = np.linspace(0, len(loss_g), len(loss_g))
    f, ax = plt.subplots(1)
   
    plt.plot(g_x, loss_g, label='loss_g')
    plt.plot(g_x, loss_d, label='loss_d')
    ax.set_xlim(0, m.epoch)

    plt.title('Vanilla Generative Adversarial Network Loss Graph')
    plt.xlabel('epoch')
    plt.ylabel('loss value')
    plt.legend()
    plt.savefig("mnist_dcgan_loss_epoch%d" %e)
    plt.close()


def convblocklayer(x, out_ch,kernel_size,stride):
    #feature = tf.Variable(tf.random_normal([kernel_size,kernel_size,x.shape[3],out_ch], stddev = 0.01))
    feature = tf.get_variable("feature",[kernel_size,kernel_size,x.shape[3],out_ch])
    g = tf.nn.conv2d(x,feature,[1,stride,stride,1],'SAME')
    m,v = tf.nn.moments(g,[0]) 
    g = tf.nn.batch_normalization(g,m,v,None,None,0.0001)
    g = tf.nn.relu(g)   
    return g

def deconvblocklayer(x,out_ch,kernel_size,stride,padding):
    #feature = tf.Variable(tf.random_normal([4,4,tf.shape(x)[1],out_ch] , stddev = 0.01))
    feature = tf.get_variable("feature",[kernel_size,kernel_size,out_ch,x.shape[3]])
    x_s = x.get_shape().as_list()
    o_s = stride*(x_s[2]-1) + kernel_size -2*padding 
    print(o_s)
    g = tf.nn.conv2d_transpose(x,feature,[x_s[0],o_s,o_s,out_ch],[1,stride,stride,1])
    m,v = tf.nn.moments(g,[0])
    g = tf.nn.batch_normalization(g,m,v,None,None,0.0001)
    g = tf.nn.relu(g)
    print(g)
    return g

def generator(input,output):
    with tf.variable_scope('deconv_layer_1'):
     g = deconvblocklayer(input,1024,4,4,0)
    with tf.variable_scope('deconv_layer_2'):
     g = deconvblocklayer(g,512,4,2,1)
    with tf.variable_scope('deconv_layer_3'):
     g = deconvblocklayer(g,256,4,2,1)
    with tf.variable_scope('deconv_layer_4'):
     g = deconvblocklayer(g,128,4,2,1)
    #feature = tf.Variable(random_normal([4,4,128,output.shape[1]], stddev = 0.01))
    o_c = output.get_shape().as_list()[3]
    with tf.variable_scope('deconv_layer_5'):
     feature = tf.get_variable("feature",[4,4,o_c,128])
    g_s = g.get_shape().as_list()
    o_s = 2*(g_s[2]-1) + 4 -2*1 
    g = tf.nn.conv2d_transpose(g,feature,[g_s[0], o_s, o_s, o_c ],[1,2,2,1])
    g = tf.nn.sigmoid(g)
    print(g)
    return g

def discriminator(input):
    with tf.variable_scope('conv_layer_1',reuse = tf.AUTO_REUSE):
     d = convblocklayer(input,128,4,2)
    with tf.variable_scope('conv_layer_2',reuse = tf.AUTO_REUSE):
     d = convblocklayer(d,256,4,2)
    with tf.variable_scope('conv_layer_3',reuse = tf.AUTO_REUSE):
     d = convblocklayer(d,512,4,2)
    with tf.variable_scope('conv_layer_4',reuse = tf.AUTO_REUSE):
     d = convblocklayer(d,1024,4,2)
    #feature = tf.Variable(random_normal([4,4,1024,1], stddev = 0.01))
    with tf.variable_scope('conv_layer_5',reuse = tf.AUTO_REUSE):
     feature = tf.get_variable("feature",[4,4,d.shape[3],1] )
    d = tf.nn.conv2d(d,feature,[1,1,1,1],'VALID')
    d = tf.nn.sigmoid(d)
    print(d)
    return d

class GAN(object):
      def __init__(self,params,input,output):
          self.bn = params.batch_size
          self.lr = params.learning_rate
          self.epoch = params.num_steps
          with tf.variable_scope('g'):
           self.g = generator(input,output)
          with tf.variable_scope('d',reuse = True):
           self.d_r = discriminator(output)
           self.d_f = discriminator(self.g)
          self.in_ph = input
          self.ou_ph = output
          vars = tf.trainable_variables()
          self.d_params = [v for v in vars if v.name.startswith('d/')]
          self.g_params = [v for v in vars if v.name.startswith('g/')]
          

def train(model,mnist):
    #saver = tf.train_Saver()
    w_img = []
    for j in range(0, mnist.train.num_examples):
     ar = mnist.train.images[j].reshape((28,28))
     img = PIL.Image.fromarray(ar)
     img = img.resize((img_size,img_size))
     np_img = np.array(img)
     w_img.append(np.expand_dims(np_img,axis = -1))
    w_img = np.asarray(w_img)
    loss_d = tf.reduce_mean(-tf.log(model.d_r)-tf.log(1-model.d_f))
    loss_g = tf.reduce_mean(-tf.log(model.d_f))
    optm_d = tf.train.AdamOptimizer(model.lr).minimize(loss_d,var_list = model.d_params)
    optm_g = tf.train.AdamOptimizer(model.lr).minimize(loss_g,var_list = model.g_params)
     
    with tf.Session() as sess:
     init = tf.global_variables_initializer()
     sess.run(init)
     
     e_loss_value_d = 0
     e_loss_value_g = 0
     for i in range(model.epoch):
      #for j in range(0, model.bn,model.bn):
      for j in range(0, w_img.shape[0],model.bn):
       z = np.random.uniform(-1. , 1., (model.bn,1,1,z_size)).astype(np.float32) 
       tp = w_img[j:j+model.bn]
       _,loss_value_d = sess.run(( optm_d ,loss_d),feed_dict = {model.in_ph:z  ,model.ou_ph:tp }) 
       _,loss_value_g = sess.run(( optm_g ,loss_g),feed_dict = {model.in_ph:z}) 
       e_loss_value_d +=loss_value_d
       e_loss_value_g +=loss_value_g
      
      print("i : %s e_loss_d:%s e_loss_g :%s" %(i, e_loss_value_d/w_img.shape[0], e_loss_value_g/w_img.shape[0]))
      generateimage(model,sess,i)
     




def main(args):
    mnist = mnist_input_data.input_data.read_data_sets(args.mnist_folder+"/",one_hot=True)
    input = tf.placeholder(tf.float32,[args.batch_size, 1,1,z_size])
    output = tf.placeholder(tf.float32,[args.batch_size,img_size,img_size,1] )
    gan = GAN(args,input,output)

    writer = tf.summary.FileWriter('.')
    train(gan,mnist)
    writer.add_graph(tf.get_default_graph())


if __name__ == '__main__' :
    main(parse_args())

