import torch
import numpy as np
from scipy.optimize import linear_sum_assignment

def alignment_loss(predictions, target, label_sizes, alpha_alignment=1000.0, alpha_backprop=100.0, return_alignment=False):
    batch_size = predictions.size(0)
    # This should probably be computed using the log_softmax
    confidences = predictions[:,:,0]
    log_one_minus_confidences = torch.log(1.0 - confidences + 1e-10)

    if target is None:
        return -log_one_minus_confidences.sum()

    locations = predictions[:,:,1:5]
    target = target[:,:,0:4]

    log_confidences = torch.log(confidences + 1e-10)

    expanded_locations = locations[:,:,None,:]
    expanded_target = target[:,None,:,:]

    expanded_locations = expanded_locations.expand(locations.size(0), locations.size(1), target.size(1), locations.size(2))
    expanded_target = expanded_target.expand(target.size(0), locations.size(1), target.size(1), target.size(2))

    #Compute All Deltas
    location_deltas = (expanded_locations - expanded_target)

    normed_difference = torch.norm(location_deltas,2,3)**2
    expanded_log_confidences = log_confidences[:,:,None].expand(locations.size(0), locations.size(1), target.size(1))
    expanded_log_one_minus_confidences = log_one_minus_confidences[:,:,None].expand(locations.size(0), locations.size(1), target.size(1))

    C = alpha_alignment/2.0 * normed_difference - expanded_log_confidences + expanded_log_one_minus_confidences

    C = C.data.cpu().numpy()
    X = np.zeros_like(C)
    if return_alignment:
        target_ind_bs=[]
        location_ind_bs=[]
    for b in range(C.shape[0]):
        l = label_sizes[b]
        if l == 0:
            if return_alignment:
                target_ind_bs.append([])
                location_ind_bs.append([])
            continue

        C_i = C[b,:,:l]
        row_ind, col_ind = linear_sum_assignment(C_i.T)
        X[b][(col_ind, row_ind)] = 1.0
        if return_alignment:
            target_ind_bs.append(row_ind)
            location_ind_bs.append(col_ind)


    X = torch.from_numpy(X).type(predictions.data.type())
    X2 = 1.0 - torch.sum(X, 2)

    location_loss = (alpha_backprop/2.0 * normed_difference * X).sum()
    confidence_loss =  -(expanded_log_confidences * X).sum() - (log_one_minus_confidences * X2).sum()

    loss = confidence_loss + location_loss

    loss = loss/batch_size

    if return_alignment:
        #for b in range(C.shape[0]):
        #    print('alignemnt')
        #    for i in range(len(target_ind_bs[b])):
        #        print('b={}, i={}, lenlocation={}, lentarget={}, lenlocation[b]={}, lentarget[b]={}'.format(b,i,len(location_ind_bs),len(target_ind_bs),len(location_ind_bs[b]),len(target_ind_bs[b])))
        #        print('location_ind_bs[b][i]={}, target_ind_bs[b][i]={}, targetsize={}, locationsize={}'.format(location_ind_bs[b][i],target_ind_bs[b][i],target.size(1),locations.size(1)))
        #        print(' gt:{},{}\tpred:{},{}'.format(locations[b,location_ind_bs[b][i],0],
        #                                             locations[b,location_ind_bs[b][i],1],
        #                                             target[b,target_ind_bs[b][i],0],
        #                                             target[b,target_ind_bs[b][i],1]))
        return loss, location_ind_bs, target_ind_bs
    return loss