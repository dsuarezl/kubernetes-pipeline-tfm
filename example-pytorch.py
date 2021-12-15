import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets
from torchvision.transforms import ToTensor, Lambda, Compose
import matplotlib.pyplot as plt

from kube_pipe_pytorch import make_kube_pipeline, make_kube_pipeline2


# Download training data from open datasets.
training_data = datasets.FashionMNIST(
    root="data",
    train=True,
    download=True,
    transform=ToTensor(),
)

# Download test data from open datasets.
test_data = datasets.FashionMNIST(
    root="data",
    train=False,
    download=True,
    transform=ToTensor(),
)


batch_size = 64

# Create data loaders.
train_dataloader = DataLoader(training_data, batch_size=batch_size)
test_dataloader = DataLoader(test_data, batch_size=batch_size)

for X, y in test_dataloader:
    print("Shape of X [N, C, H, W]: ", X.shape)
    print("Shape of y: ", y.shape, y.dtype)
    break

device = "cuda" if torch.cuda.is_available() else "cpu"

# Define model
class NeuralNetwork(nn.Module):
    def __init__(self):
        super(NeuralNetwork, self).__init__()
        self.flatten = nn.Flatten()
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(28*28, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 10)
        )

    def forward(self, x):
        x = self.flatten(x)
        logits = self.linear_relu_stack(x)
        return logits

model = NeuralNetwork().to(device)

loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(model.parameters(), lr=1e-3)


def train_fn(dataloader, model, loss_fn, optimizer):
    size = len(dataloader.dataset)
    model.train()
    for batch, (X, y) in enumerate(dataloader):
        X, y = X.to(device), y.to(device)

        # Compute prediction error
        pred = model(X)
        loss = loss_fn(pred, y)

        # Backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch % 100 == 0:
            loss, current = loss.item(), batch * len(X)
            print(f"loss: {loss:>7f}  [{current:>5d}/{size:>5d}]")


def test_fn(dataloader, model, loss_fn):
    size = len(dataloader.dataset)
    num_batches = len(dataloader)
    model.eval()
    test_loss, correct = 0, 0
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            pred = model(X)
            test_loss += loss_fn(pred, y).item()
            correct += (pred.argmax(1) == y).type(torch.float).sum().item()
    test_loss /= num_batches
    correct /= size
    print(f"Test Error: \n Accuracy: {(100*correct):>0.1f}%, Avg loss: {test_loss:>8f} \n")


#init : funciones de train y test,  model, loss_fn, optimizer, 
# 
#start : datasets de train y test, optional epochs = 5


pipeline = make_kube_pipeline([{x:train},{ "loss_fn" : loss_fn, 
                                "train_fn" : train_fn,
                                "test_fn" : test_fn, 
                                "optimizer" : optimizer,   
                                "model" : model}])


pipeline = make_kube_pipeline2([loss_fn,train_fn,test_fn,optimizer,model],

                               [loss_fn,train_fn,test_fn,optimizer,model])



pipeline.config( resources = {"memory" :  "100Mi"})


#Train loop
def train_loop():
    epochs = 5
    for t in range(epochs):
        print("Epoch ", t+1)
        train_fn(training_data, model, loss_fn, optimizer)
        
        test_fn(test_data, model, loss_fn)
    print("Done!")


pipeline = make_kube_pipeline3(train_loop) 


#pipeline = pipeline.train(train_dataloader,test_dataloader, epochs = 1, resources = {"memory" :  "100Mi"})

pipeline = pipeline.train(train_dataloader,test_dataloader, epochs = 1)

model = pipeline.getModel(0)

test_fn(test_dataloader,model,loss_fn)