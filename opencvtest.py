from cv2 import NORM_L1, NORM_L2, NORM_MINMAX
import numpy as np
import cv2 as cv
import math 

class CntCirc:
  def __init__(self,x,y,r):
    self.x = x
    self.y = y
    self.r = r

def contoursToCircles(cnts):
    circles = []
    for cnt in cnts:
     (x,y),radius = cv.minEnclosingCircle(cnt)
     center = (int(x),int(y))
     radius = int(radius)
     circ = CntCirc(x,y,radius)
     circles.append(circ)
     cards = set()
    return circles

def circlesToPairs(circs):
    pairs = []
    for c1 in circs:
      for c2 in circs:
        if c1.r*0.4 < c2.r < c1.r*0.9:
            cat1=(c2.x-c1.x)
            cat2=(c2.y-c1.y)
            if cat1 == 0:
                cat1 = 1
            if (c1.r*1.7)**2 < cat1**2+cat2**2 < (c1.r*2.5)**2:
                ang = math.degrees(math.atan(cat2/cat1))
                if c1.x>c2.x:
                    ang = ang+180
                pairs.append((c1,c2,ang))
    return pairs

vals = ['7','8','9','10','j','q','q2','k','a']
redTips = [2,3]# doba,rosu
blackTips = [0,1]# cruce,verde

def valueSeek(cardContent,V,A):
    rmatrix = cv.getRotationMatrix2D((V.r,V.r),A-90,1)
    cropval = cardContent[int(V.y-V.r):int(V.y+V.r),int(V.x-V.r):int(V.x+V.r)]
    cropval = cv.warpAffine(cropval,rmatrix,(V.r*2,V.r*2))
    rmatrix = cv.getRotationMatrix2D((V.r,V.r),A-90,1)
    cropval = cv.resize(cropval,(30,30))
    cropval = cropval[0:30,5:25]
    for i in range(30):
        for j in range(20):
            cropval[i,j]= 0 if cropval[i,j]<100 else 255
    sumval = []
    for val in vals:
        imcg = cv.bitwise_xor(cv.imread('etalon\\'+val+'.jpg',cv.IMREAD_GRAYSCALE),cropval)
        summ=sum(sum(imcg))
 #cv.imshow(str(summ)+' '+str(V.r),imcg)
        sumval.append(summ)
    if min(sumval)<2000:
        return (vals[sumval.index(min(sumval))])[0]
    else:
        return None

def imgToCards(img):
#img = cv.imread('carti7.png')
#cv.imshow('ab',img)

    imgblur = cv.GaussianBlur(img,(3,1),cv.BORDER_CONSTANT)
#cv.imshow('blurredBGR',imgblur)

    wtf,imgt = cv.threshold(imgblur,125,255,cv.THRESH_BINARY)
#cv.imshow('threshh',imgt)

    b,g,r = cv.split(imgt)
    kernel = np.ones((2,2), np.uint8)
    reds = cv.subtract(r,cv.bitwise_and(g,b))
    reds = cv.dilate(reds,kernel,iterations=1)
    wtf,reds = cv.threshold(reds,125,255,cv.THRESH_BINARY)
    #cv.imshow('reds',reds)

    kernel = np.ones((1,1), np.uint8)
    blacks = cv.bitwise_not(cv.bitwise_or(r,cv.bitwise_or(g,b)))
    blacks = cv.dilate(blacks,kernel,iterations=1)
    #cv.imshow('blacks',blacks)

    rsg = cv.subtract(r,g)
#rsg = cv.subtract(rsg,b)
    nb = cv.bitwise_not(b)
    ng = cv.bitwise_not(g)
    nr = cv.bitwise_not(r)
    nbgr = cv.bitwise_and(nb,cv.bitwise_and(ng,nr))
    bgr = cv.bitwise_and(b,cv.bitwise_and(g,r))
#cv.imshow('bgr',bgr)

    bz,whiteThresh = cv.threshold(bgr,40,255,cv.THRESH_BINARY)
#cv.imshow('thresh',whiteThresh)

    whiteExt,h = cv.findContours(whiteThresh,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)


#cv.drawContours(blank,c,-1,(255,255,255),1)
#cv.imshow('bkl',blank)
#whiteFilt = []
#for cnt in whiteExt:
#    if cv.contourArea(cnt)>100:
#      whiteFilt.append(cnt)
    blackimg = np.zeros(whiteThresh.shape,'uint8')
    cv.drawContours(blackimg,whiteExt,-1,(255,255,255),-1)
#cv.imshow('bkl',blackimg)
    cardContent = cv.bitwise_xor(whiteThresh,blackimg)

    cardContentX,stuff = cv.findContours(cardContent,cv.RETR_TREE,cv.CHAIN_APPROX_SIMPLE)
    cardContentCircs = contoursToCircles(cardContentX)

    cards = [set(),set(),set(),set()]

    RED = cv.bitwise_and(reds,cardContent)
#cv.imshow('RED',RED)
    REDcnts,stuff = cv.findContours(RED,cv.RETR_TREE,cv.CHAIN_APPROX_SIMPLE)
    REDcircs = contoursToCircles(REDcnts)
    REDpairs = circlesToPairs(REDcircs)
    for V,T,A in REDpairs:
    #RED Value
        cardval = valueSeek(cardContent,V,A)
        if cardval is None:
            continue
        else:
            cv.circle(img,(int(V.x),int(V.y)),V.r,(0,0,255),2)
    #RED tip
    
        rmatrix = cv.getRotationMatrix2D((T.r,T.r),A-90,1)
        croptip = cardContent[int(T.y-T.r):int(T.y+T.r),int(T.x-T.r):int(T.x+T.r)]
        croptip = cv.warpAffine(croptip,rmatrix,(T.r*2,T.r*2))
        croptip = cv.resize(croptip,(15,15))
        for i in range(15):
            for j in range(15):
                croptip[i,j]= 0 if croptip[i,j]<100 else 255
        sumtip = []
        for tip in redTips:
            imcg = cv.bitwise_xor(cv.imread('etalon/'+str(tip)+'.jpg',cv.IMREAD_GRAYSCALE),croptip)
            summ=sum(sum(imcg))
            sumtip.append(summ)
        cardtip = redTips[sumtip.index(min(sumtip))]
        if min(sumtip)<500:
            cv.circle(img,(int(T.x),int(T.y)),T.r,(0,255,255),2)
            cards[cardtip].add(cardval)

    BLA = cv.bitwise_and(blacks,cardContent)
    #cv.imshow('BLA',BLA)
    BLAcnts,stuff = cv.findContours(BLA,cv.RETR_TREE,cv.CHAIN_APPROX_SIMPLE)
    BLAcircs = contoursToCircles(BLAcnts)
    BLApairs = circlesToPairs(BLAcircs)
    for V,T,A in BLApairs:
        #BLACK value
        cardval = valueSeek(cardContent,V,A)
        if cardval is None:
            continue
        else:
            cv.circle(img,(int(V.x),int(V.y)),V.r,(255,0,0),2)
        #BLACK tip
        rmatrix = cv.getRotationMatrix2D((T.r,T.r),A-90,1)
        croptip = cardContent[int(T.y-T.r):int(T.y+T.r),int(T.x-T.r):int(T.x+T.r)]
        croptip = cv.warpAffine(croptip,rmatrix,(T.r*2,T.r*2))
        croptip = cv.resize(croptip,(60,60))
        #croptip = croptip[0:10,0:30]
        for i in range(60):
            for j in range(60):
                croptip[i,j]= 0 if croptip[i,j]<125 else 255
        cv.transpose(croptip,croptip)
        #cv.imwrite(str(T.x)+'.png',croptip)
        sumtip = []
        #tt = croptip.astype('int32')
        #tt = sum(tt)
        #for i in range(15):
        #    if tt[i+1]+1<tt[i]:
        #        cardtip = 0
        #        break
        #    cardtip = 1
        #cv.imshow(cardtip+str(T.x),croptip)
        #zeropoint=croptip[20,8]
        for tip in blackTips:
            etalon = cv.imread('etalon/'+str(tip)+'.png',cv.IMREAD_GRAYSCALE)
            #for i in range(60):
            #    for j in range(60):
            #        etalon[i,j]= 0 if etalon[i,j]<125 else 1
            imcg = cv.bitwise_xor(etalon,croptip)
            summ=cv.countNonZero(imcg)
            #cv.imshow(str(summ)+' '+str(T.r),imcg)
            sumtip.append(summ)
        #cv.imshow(str(summ)+tip+str(T.x-V.x),imcg)
        
        cardtip = blackTips[sumtip.index(min(sumtip))]
        #if min(sumtip)<8000:
        cv.circle(img,(int(T.x),int(T.y)),T.r,(255,255,0),2)
        cards[cardtip].add(cardval)
        #    print((cardval,cardtip))
    cv.imwrite('result.jpg',img)
    #cv.waitKey(1)
    return cards

#img = cv.imread('test.jpg')
#print(imgToCards(img))
#cv.imshow('',img)
#cv.waitKey(0)



#cv.imshow('final',img)
#cv.waitKey(0)