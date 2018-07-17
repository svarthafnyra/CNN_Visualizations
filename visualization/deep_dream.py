"""
Created on Mon Nov 21 21:57:29 2017

@author: Utku Ozbulak - github.com/utkuozbulak
"""
import os
import cv2
from matplotlib import pyplot as plt
from attacks import attack
import torch
from torch.optim import SGD
from torchvision import models

from misc_functions import preprocess_image, recreate_image,get_params

class DeepDream():
    """
        Produces an image that minimizes the loss of a convolution
        operation for a specific layer and filter
    """
    def __init__(self, model, selected_layer, selected_filter, im_path):
        self.model = model
        self.model.eval()
        self.selected_layer = selected_layer
        self.selected_filter = selected_filter
        self.conv_output = 0
        # Generate a random image
        self.created_image = cv2.imread(im_path, 1)
        # Hook the layers to get result of the convolution
        self.hook_layer()

    def hook_layer(self):
        def hook_function(module, grad_in, grad_out):
            # Gets the conv output of the selected filter (from selected layer)
            self.conv_output = grad_out[0, self.selected_filter]

        # Hook the selected layer
        self.model[self.selected_layer].register_forward_hook(hook_function)

    def dream(self,name,iters):
        # Process image and return variable
        self.processed_image = preprocess_image(self.created_image, False)
        # Define optimizer for the image
        # Earlier layers need higher learning rates to visualize whereas layer layers need less
        optimizer = SGD([self.processed_image], lr=12,  weight_decay=1e-4)
        for i in range(1, iters+1):
            optimizer.zero_grad()
            # Assign create image to a variable to move forward in the model
            x = self.processed_image
            for index, layer in enumerate(self.model):
                # Forward
                x = layer(x)
                # Only need to forward until we the selected layer is reached
                if index == self.selected_layer:
                    break
            # Loss function is the mean of the output of the selected layer/filter
            # We try to minimize the mean of the output of that specific filter
            loss = -torch.mean(self.conv_output)
            print('Iteration:', str(i), 'Loss:', "{0:.2f}".format(loss.data.numpy()))
            # Backward
            loss.backward()
            # Update image
            optimizer.step()
            # Recreate image
            self.created_image = recreate_image(self.processed_image)
            # Save image every X iteration
            if i % 50 == 0: # Change 50 if you want
                cv2.imwrite('results/'+name + str(self.selected_layer) +
                            '_f' + str(self.selected_filter) + '_iter'+str(i)+'.jpg',
                            self.created_image)

        return self.created_image

def runDeepDream(choose_network = 'VGG19',
                 target_example = 3,
                 attack_type = 'FGSM',
                 cnn_layer = 34,
                 filter_pos = 94,
                 iters = 50):

    #if __name__ == '__main__':

    if choose_network == 'VGG19':
        pretrained_model = models.vgg19(pretrained=True).features
    if choose_network == 'AlexNet':
        pretrained_model = models.AlexNet(pretrained = True).features

    if target_example == 3:
        im_path = 'input_images/volcano.jpg'
    elif target_example == 0:
        im_path = 'input_images/snake.jpg'
    elif target_example ==1:
        im_path = 'iput_images/cat_dog.jpg'
    elif target_example ==2:
        im_path = 'input_images/spider.jpg'

    # Fully connected layer is not needed

    dd = DeepDream(pretrained_model, cnn_layer, filter_pos, im_path)
    # This operation can also be done without Pytorch hooks
    # See layer visualisation for the implementation without hooks
    (original_image, prep_img, target_class, file_name_to_export, pretrained_model) = get_params(target_example,choose_network)
    result = dd.dream(file_name_to_export,iters)
    fig = plt.figure()
    fig.suptitle(file_name_to_export+' - '+attack_type+' - Deep Dream '+str(cnn_layer))
    ax1 = fig.add_subplot(2,1,1)
    ax1.imshow(result)
    ax1.set_title('Natural Dream')
# Attack:
    attack(attack_type,pretrained_model,original_image,'DeepDream',target_class)
    im_path = 'results/DeepDream_'+attack_type+'_Attack.jpg'
    dd2 = DeepDream(pretrained_model.features, cnn_layer, filter_pos, im_path)

    result2 = dd2.dream(file_name_to_export+'_'+attack_type,iters)

    ax2 = fig.add_subplot(2,1,2)
    ax2.imshow(result2)
    ax2.set_title('Adversary Dream')

    fig.set_size_inches(18.5, 10.5)
    fig.savefig('Concise Results/'+file_name_to_export+'_'+attack_type+' - Deep Dream '+str(cnn_layer),dpi = 100)
