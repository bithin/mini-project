from pylab import figure,pie,show
N, red, blue, green = 500, 100, 300, 100
figure(figsize=(6,6))
pie((red,blue,green),labels=('red','blue','green'),colors=('red','blue','green'),)
show()
